// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// App-local XInput forwarding DLL. Localization and text layout only.
// Changes to the game occur in memory; this DLL never writes EXEs or saves.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <Xinput.h>
#include <string>
#include <vector>
#include <algorithm>
#include <cstdio>
#include <intrin.h>
#include "generated.hpp"

namespace {
BYTE* game;
DWORD imageSize;
bool active=false;
wchar_t logPath[32768]{};
void* layoutReturns[8]{};
decltype(&LoadStringA) loadStringOriginal;
decltype(&CreateFontA) fontOriginal;
decltype(&DrawTextA) drawOriginal;
decltype(&DrawTextExA) drawExOriginal;
decltype(&TextOutA) textOriginal;
decltype(&GetTextExtentPoint32A) extentOriginal;
decltype(&MessageBoxA) messageOriginal;

void log(const char* value) {
    FILE* f=nullptr;
    if(_wfopen_s(&f,logPath,L"ab")==0 && f) {fprintf(f,"%s\r\n",value);fclose(f);}
}
bool inside(const void* p,size_t n) {
    auto q=reinterpret_cast<uintptr_t>(p),start=reinterpret_cast<uintptr_t>(game);
    return q>=start && n<=imageSize && q-start<=imageSize-n;
}
bool write(void* destination,const void* data,size_t size) {
    DWORD old=0,unused=0;
    if(!VirtualProtect(destination,size,PAGE_EXECUTE_READWRITE,&old))return false;
    memcpy(destination,data,size);
    FlushInstructionCache(GetCurrentProcess(),destination,size);
    return VirtualProtect(destination,size,old,&unused)!=0;
}
bool containsChinese(const std::wstring& s) {
    for(auto c:s)if(c>=0x3400 && c<=0x9fff)return true;
    return false;
}
std::wstring wide(const char* s,int n) {
    if(!s)return {};
    if(n<0)n=static_cast<int>(strlen(s));
    int size=MultiByteToWideChar(936,MB_ERR_INVALID_CHARS,s,n,nullptr,0);
    std::wstring out(size,L'\0');
    if(size)MultiByteToWideChar(936,MB_ERR_INVALID_CHARS,s,n,&out[0],size);
    return out;
}
std::wstring displayText(const char* s,int n) {
    auto out=wide(s,n);
    if(out==L"On")return L"开";
    if(out==L"Off")return L"关";
    return out;
}

int WINAPI loadStringHook(HINSTANCE module,UINT id,LPSTR output,int capacity) {
    wchar_t original[8192]{};
    int count=LoadStringW(module,id,original,8192);
    if(count>0 && output && capacity>0) {
        const Translation* selected=nullptr;
        if(reinterpret_cast<BYTE*>(module)==game)for(const auto& item:startupTranslations) {
            if(item.id==id && (!wcscmp(item.english,original) || !wcscmp(item.chinese,original))) {selected=&item;break;}
        }
        if(!selected)for(const auto& item:translations) {
            if(item.id==id && (!wcscmp(item.english,original) || !wcscmp(item.previous,original) || !wcscmp(item.chinese,original))) {selected=&item;break;}
        }
        if(!selected)for(const auto& item:translations)if(!wcscmp(item.english,original)){selected=&item;break;}
        if(selected) {
            int length=static_cast<int>(strlen(selected->encoded));
            int used=std::min(length,capacity-1);
            // Truncation must never split a GBK lead/trail byte pair.
            int complete=0;
            while(complete<used) {
                int step=IsDBCSLeadByteEx(936,static_cast<BYTE>(selected->encoded[complete]))?2:1;
                if(complete+step>used)break;
                complete+=step;
            }
            memcpy(output,selected->encoded,complete);output[complete]=0;
            return complete;
        }
    }
    return loadStringOriginal(module,id,output,capacity);
}

HFONT WINAPI fontHook(int h,int w,int esc,int orient,int weight,DWORD italic,DWORD underline,DWORD strike,
                     DWORD charset,DWORD out,DWORD clip,DWORD quality,DWORD pitch,LPCSTR face) {
    // Wingdings is a symbolic selection arrow, not prose.
    if(face && (!_stricmp(face,"Wingdings") || !_stricmp(face,"Webdings")))
        return fontOriginal(h,w,esc,orient,weight,italic,underline,strike,charset,out,clip,quality,pitch,face);
    // The released Chinese EXE already applies the 75% font adapter.
    // Do not apply it for a second time when upgrading an installed game.
    if((!face || _stricmp(face,"SimHei")) && abs(h)>=24)h=h*3/4;
    return CreateFontW(h,w,esc,orient,weight,italic,underline,strike,GB2312_CHARSET,out,clip,quality,pitch,L"SimHei");
}

struct FitFont {
    HDC dc;HGDIOBJ prior=nullptr;HFONT temporary=nullptr;
    FitFont(HDC target,const std::wstring& text,int width,int height,UINT flags,LPDRAWTEXTPARAMS params=nullptr):dc(target) {
        if(!containsChinese(text) || width<=0)return;
        LOGFONTW lf{};
        if(!GetObjectW(GetCurrentObject(dc,OBJ_FONT),sizeof(lf),&lf))return;
        UINT measure=(flags & ~(DT_END_ELLIPSIS|DT_PATH_ELLIPSIS|DT_WORD_ELLIPSIS|DT_MODIFYSTRING|DT_VCENTER|DT_BOTTOM|DT_NOCLIP))|DT_CALCRECT;
        int originalHeight=std::max(1,static_cast<int>(abs(lf.lfHeight)));
        const int sign=lf.lfHeight<0?-1:1;
        auto selectHeight=[&](int h) {
            if(temporary){SelectObject(dc,prior);DeleteObject(temporary);temporary=nullptr;}
            if(h==originalHeight)return true;
            lf.lfHeight=sign*h;lf.lfWidth=0;
            temporary=CreateFontIndirectW(&lf);
            if(!temporary)return false;
            auto previous=SelectObject(dc,temporary);if(!prior)prior=previous;
            return true;
        };
        auto fits=[&]() {
            RECT measured{0,0,width,height>0?height:30000};
            DRAWTEXTPARAMS copy{};if(params)copy=*params;
            DrawTextExW(dc,const_cast<wchar_t*>(text.c_str()),static_cast<int>(text.size()),&measured,measure,params?&copy:nullptr);
            return measured.right-measured.left<=width && (height<=0 || measured.bottom-measured.top<=height);
        };
        if(fits())return;
        // Select one font for the complete string. Measurement and both shadow
        // passes use identical limits; CALCRECT never uses the output rectangle
        // of a different font as a new fitting constraint.
        int low=std::min(8,originalHeight),high=originalHeight-1,best=low;
        while(low<=high) {
            int mid=low+(high-low)/2;
            if(!selectHeight(mid))return;
            if(fits()){best=mid;low=mid+1;}else high=mid-1;
        }
        selectHeight(best);
    }
    ~FitFont(){if(temporary){SelectObject(dc,prior);DeleteObject(temporary);}}
};
int WINAPI drawHook(HDC dc,LPCSTR text,int length,LPRECT rect,UINT flags) {
    if(!text || !rect)return drawOriginal(dc,text,length,rect,flags);
    auto value=displayText(text,length);
    if(!containsChinese(value))return drawOriginal(dc,text,length,rect,flags);
    // No generic font fitting here: the race HUD and scrolling credits retain
    // their original layout and font metrics.
    return DrawTextW(dc,value.c_str(),static_cast<int>(value.size()),rect,flags & ~DT_MODIFYSTRING);
}
int layoutKind(void* address) {
    for(int i=0;i<8;++i)if(layoutReturns[i] && layoutReturns[i]==address)return i;
    return -1;
}
int wideDrawEx(HDC dc,std::wstring& value,LPRECT rect,UINT flags,LPDRAWTEXTPARAMS params) {
    DRAWTEXTPARAMS local{};if(params)local=*params;
    int result=DrawTextExW(dc,&value[0],static_cast<int>(value.size()),rect,flags & ~DT_MODIFYSTRING,params?&local:nullptr);
    if(params) {
        // The game consumes ANSI byte counts, not UTF-16 character counts.
        size_t count=std::min(static_cast<size_t>(local.uiLengthDrawn),value.size());
        params->uiLengthDrawn=static_cast<UINT>(WideCharToMultiByte(936,0,value.data(),static_cast<int>(count),nullptr,0,nullptr,nullptr));
    }
    return result;
}
int WINAPI drawExHook(HDC dc,LPSTR text,int length,LPRECT rect,UINT flags,LPDRAWTEXTPARAMS params) {
    if(!text || !rect)return drawExOriginal(dc,text,length,rect,flags,params);
    auto value=displayText(text,length);
    if(!containsChinese(value))return drawExOriginal(dc,text,length,rect,flags,params);
    int site=layoutKind(_ReturnAddress());
    int width=0,height=0;
    if(site==1 || site==2) {width=608;flags|=DT_SINGLELINE;}
    if(site>=3 && site<=5) {
        if(flags&DT_SINGLELINE) {width=608;height=30;}
        else if(rect->right-rect->left<=320) {width=300;height=246;}
    }
    if((site==6 || site==7) && value.size()>20 && rect->right>rect->left && rect->bottom>rect->top) {
        width=rect->right-rect->left;height=rect->bottom-rect->top;
    }
    if(width) {
        FitFont fit(dc,value,width,height,flags,params);
        return wideDrawEx(dc,value,rect,flags & ~(DT_END_ELLIPSIS|DT_PATH_ELLIPSIS|DT_WORD_ELLIPSIS),params);
    }
    return wideDrawEx(dc,value,rect,flags,params);
}
BOOL WINAPI textHook(HDC dc,int x,int y,LPCSTR text,int length) {
    if(!text)return textOriginal(dc,x,y,text,length);
    auto value=displayText(text,length);
    if(!containsChinese(value))return textOriginal(dc,x,y,text,length);
    return TextOutW(dc,x,y,value.c_str(),static_cast<int>(value.size()));
}
BOOL WINAPI extentHook(HDC dc,LPCSTR text,int count,LPSIZE size) {
    auto value=displayText(text,count);
    if(containsChinese(value)) {
        if(layoutKind(_ReturnAddress())==0) {
            FitFont fit(dc,value,608,0,DT_SINGLELINE|DT_NOPREFIX);
            return GetTextExtentPoint32W(dc,value.c_str(),static_cast<int>(value.size()),size);
        }
        return GetTextExtentPoint32W(dc,value.c_str(),static_cast<int>(value.size()),size);
    }
    return extentOriginal(dc,text,count,size);
}
int WINAPI messageHook(HWND window,LPCSTR text,LPCSTR caption,UINT type) {
    auto value=displayText(text,-1),title=displayText(caption,-1);
    if(containsChinese(value) || containsChinese(title))return MessageBoxW(window,value.c_str(),title.c_str(),type);
    return messageOriginal(window,text,caption,type);
}

const char* __fastcall assetName(unsigned char index) {
    static const char* names[]={"Thrash","Axle","Bose","Cydney","Jon","Pearl","Rhonda","Jim","Mike"};
    return index<9?names[index]:nullptr;
}
std::vector<BYTE*> matches(const Pattern& pattern) {
    std::vector<BYTE*> hits;
    auto nt=reinterpret_cast<IMAGE_NT_HEADERS32*>(game+reinterpret_cast<IMAGE_DOS_HEADER*>(game)->e_lfanew);
    auto section=IMAGE_FIRST_SECTION(nt);
    for(WORD s=0;s<nt->FileHeader.NumberOfSections;++s,++section) {
        if(!(section->Characteristics&IMAGE_SCN_MEM_EXECUTE))continue;
        auto p=game+section->VirtualAddress;size_t size=section->Misc.VirtualSize;
        if(!inside(p,size) || size<pattern.size)continue;
        for(size_t i=0;i<=size-pattern.size;++i) {
            bool match=true;
            for(size_t j=0;j<pattern.size;++j)if(pattern.mask[j] && p[i+j]!=pattern.bytes[j]){match=false;break;}
            if(match)hits.push_back(p+i);
        }
    }
    return hits;
}
bool matchAt(const BYTE* p,const BYTE* bytes,const BYTE* mask,size_t size) {
    if(!inside(p,size))return false;
    for(size_t i=0;i<size;++i)if(mask[i] && p[i]!=bytes[i])return false;
    return true;
}
void locateLayouts() {
    for(size_t i=0;i<8;++i) {
        const auto& site=layoutSites[i];
        BYTE* start=game+site.rva;
        if(!matchAt(start,site.bytes,site.mask,site.size)) {
            Pattern p{site.bytes,site.mask,site.size,site.returnOffset,1};
            auto found=matches(p);
            if(found.size()!=1){log(site.name);continue;}
            start=found[0];
        }
        layoutReturns[i]=start+site.returnOffset;
    }
}
struct Change {
    void* address;std::vector<BYTE> before,after;
    Change(void* p,const void* bytes,size_t n):address(p),before(static_cast<BYTE*>(p),static_cast<BYTE*>(p)+n),
        after(static_cast<const BYTE*>(bytes),static_cast<const BYTE*>(bytes)+n){}
};
void addExecutableText(std::vector<Change>& changes) {
    // The legacy installer edited these immutable error messages on disk.
    // For an untouched EXE, retain the same translations only in memory.
    // An already translated EXE has no matching English literals and is left alone.
    auto nt=reinterpret_cast<IMAGE_NT_HEADERS32*>(game+reinterpret_cast<IMAGE_DOS_HEADER*>(game)->e_lfanew);
    for(const auto& item:executableLiterals) {
        std::vector<BYTE*> hits;
        const size_t size=strlen(item.english)+1;
        auto section=IMAGE_FIRST_SECTION(nt);
        for(WORD s=0;s<nt->FileHeader.NumberOfSections;++s,++section) {
            if(!(section->Characteristics&IMAGE_SCN_CNT_INITIALIZED_DATA) ||
               (section->Characteristics&(IMAGE_SCN_MEM_EXECUTE|IMAGE_SCN_MEM_WRITE)))continue;
            BYTE* start=game+section->VirtualAddress;
            size_t length=section->Misc.VirtualSize;
            if(length<size || !inside(start,length))continue;
            for(size_t i=0;i+size<=length;++i)
                if((!i || start[i-1]==0) && !memcmp(start+i,item.english,size))hits.push_back(start+i);
        }
        if(hits.size()!=1)continue;
        std::vector<BYTE> replacement(size,0);
        memcpy(replacement.data(),item.chinese,strlen(item.chinese));
        changes.emplace_back(hits[0],replacement.data(),size);
    }
}
void addAlternateNames(std::vector<Change>& changes) {
    auto nt=reinterpret_cast<IMAGE_NT_HEADERS32*>(game+reinterpret_cast<IMAGE_DOS_HEADER*>(game)->e_lfanew);
    auto section=IMAGE_FIRST_SECTION(nt);
    std::vector<DWORD*> tables;
    for(WORD s=0;s<nt->FileHeader.NumberOfSections;++s,++section) {
        if(!(section->Characteristics&IMAGE_SCN_MEM_WRITE) || (section->Characteristics&IMAGE_SCN_MEM_EXECUTE))continue;
        size_t size=section->Misc.VirtualSize;
        BYTE* start=game+section->VirtualAddress;
        if(!inside(start,size) || size<sizeof(DWORD)*12)continue;
        for(size_t i=0;i+sizeof(DWORD)*12<=size;i+=4) {
            auto table=reinterpret_cast<DWORD*>(start+i);
            bool same=true;
            for(size_t j=0;j<12;++j) {
                auto text=reinterpret_cast<const char*>(table[j]);
                size_t length=strlen(alternateNames[j].original)+1;
                if(!inside(text,length) || memcmp(text,alternateNames[j].original,length)){same=false;break;}
            }
            if(same)tables.push_back(table);
        }
    }
    if(tables.size()!=1){log("Alternate NPC names: local table not recognized; left unchanged");return;}
    for(size_t i=0;i<12;++i) {
        auto value=alternateNames[i].translated;
        changes.emplace_back(tables[0]+i,&value,sizeof value);
    }
}
bool initialize() {
    auto dos=reinterpret_cast<IMAGE_DOS_HEADER*>(game);
    if(dos->e_magic!=IMAGE_DOS_SIGNATURE)return false;
    auto nt=reinterpret_cast<IMAGE_NT_HEADERS32*>(game+dos->e_lfanew);
    if(nt->Signature!=IMAGE_NT_SIGNATURE || nt->FileHeader.Machine!=IMAGE_FILE_MACHINE_I386)return false;
    imageSize=nt->OptionalHeader.SizeOfImage;
    std::vector<BYTE*> calls;
    BYTE* common=nullptr;
    bool legacyNames=false;
    for(const auto& pattern:patterns) {
        auto found=matches(pattern);
        if(found.size()!=pattern.count)return false;
        for(auto start:found) {
            auto call=start+pattern.call;
            if(!inside(call,5) || *call!=0xe8)return false;
            auto target=call+5+*reinterpret_cast<int*>(call+1);
            if(!inside(target,5))return false;
            if(*target==0xe9)target+=5+*reinterpret_cast<int*>(target+1);
            const BYTE signature[]={0x0f,0xb6,0xc1,0x83,0xf8,0x08};
            const BYTE legacy[]={0x52,0x0f,0xb6,0xc1,0x83,0xf8,0x08,0x77,0x0d,0xe8,0,0,0,0,0x5a,0xc1,0xe0,0x03,0x8d,0x44,0x02,0x0a,0x5a,0xc3};
            bool isOriginal=inside(target,sizeof signature) && !memcmp(target,signature,sizeof signature);
            bool isLegacy=inside(target,sizeof legacy+72) && !memcmp(target,legacy,sizeof legacy);
            if(isLegacy)for(unsigned n=0;n<9;++n) {
                const char* expected=assetName(static_cast<unsigned char>(n));
                if(memcmp(target+sizeof legacy+n*8,expected,strlen(expected)+1)){isLegacy=false;break;}
            }
            if(!isOriginal && !isLegacy)return false;
            if(common && common!=target)return false;
            common=target;legacyNames=isLegacy;calls.push_back(call);
        }
    }
    struct Hook {const char* name;void* function;void** original;void** slot;};
    Hook hooks[]={
        {"LoadStringA",reinterpret_cast<void*>(&loadStringHook),reinterpret_cast<void**>(&loadStringOriginal),nullptr},
        {"CreateFontA",reinterpret_cast<void*>(&fontHook),reinterpret_cast<void**>(&fontOriginal),nullptr},
        {"DrawTextA",reinterpret_cast<void*>(&drawHook),reinterpret_cast<void**>(&drawOriginal),nullptr},
        {"DrawTextExA",reinterpret_cast<void*>(&drawExHook),reinterpret_cast<void**>(&drawExOriginal),nullptr},
        {"TextOutA",reinterpret_cast<void*>(&textHook),reinterpret_cast<void**>(&textOriginal),nullptr},
        {"GetTextExtentPoint32A",reinterpret_cast<void*>(&extentHook),reinterpret_cast<void**>(&extentOriginal),nullptr},
        {"MessageBoxA",reinterpret_cast<void*>(&messageHook),reinterpret_cast<void**>(&messageOriginal),nullptr},
    };
    auto descriptor=reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(game+nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);
    for(;inside(descriptor,sizeof *descriptor) && descriptor->Name;++descriptor) {
        if(!descriptor->OriginalFirstThunk)continue;
        auto names=reinterpret_cast<IMAGE_THUNK_DATA32*>(game+descriptor->OriginalFirstThunk);
        auto slots=reinterpret_cast<IMAGE_THUNK_DATA32*>(game+descriptor->FirstThunk);
        for(;inside(names,sizeof *names)&&inside(slots,sizeof *slots)&&names->u1.AddressOfData;++names,++slots) {
            if(IMAGE_SNAP_BY_ORDINAL32(names->u1.Ordinal))continue;
            auto name=reinterpret_cast<IMAGE_IMPORT_BY_NAME*>(game+names->u1.AddressOfData);
            if(!inside(name,64))return false;
            for(auto& hook:hooks)if(!strcmp(hook.name,reinterpret_cast<const char*>(name->Name)))hook.slot=reinterpret_cast<void**>(&slots->u1.Function);
        }
    }
    for(auto& hook:hooks)if(!hook.slot || !*hook.slot)return false;
    locateLayouts();
    // Save every original byte before modifying any destination. Initialization
    // failure rolls back the complete set, including already installed imports.
    std::vector<Change> changes;
    for(auto& hook:hooks){*hook.original=*hook.slot;changes.emplace_back(hook.slot,&hook.function,sizeof(void*));}
    if(!legacyNames)for(auto call:calls) {
        BYTE branch[5]={0xe8};
        *reinterpret_cast<int*>(branch+1)=static_cast<int>(reinterpret_cast<BYTE*>(&assetName)-(call+5));
        changes.emplace_back(call,branch,sizeof branch);
    }
    addAlternateNames(changes);
    addExecutableText(changes);
    for(size_t i=0;i<changes.size();++i)if(!write(changes[i].address,changes[i].after.data(),changes[i].after.size())) {
        for(size_t j=i+1;j>0;--j)write(changes[j-1].address,changes[j-1].before.data(),changes[j-1].before.size());
        log("Text hook initialization failed; original bytes restored");
        return false;
    }
    log(legacyNames?"Chinese text hooks active; existing portrait/font adapters retained":"Chinese text hooks active; original portrait identifiers retained");
    return true;
}
HMODULE systemXinput() {
    static HMODULE module=[](){
        wchar_t path[MAX_PATH]{};
        UINT n=GetSystemDirectoryW(path,MAX_PATH);
        if(!n || n+19>=MAX_PATH)return static_cast<HMODULE>(nullptr);
        wcscat_s(path,L"\\xinput9_1_0.dll");
        auto result=LoadLibraryExW(path,nullptr,LOAD_LIBRARY_SEARCH_SYSTEM32);
        if(!result)log("System XInput could not be loaded");
        return result;
    }();
    return module;
}
}

extern "C" DWORD WINAPI ZH_XInputGetState(DWORD index,XINPUT_STATE* state) {
    static auto function=reinterpret_cast<decltype(&XInputGetState)>(GetProcAddress(systemXinput(),"XInputGetState"));
    return function?function(index,state):ERROR_DEVICE_NOT_CONNECTED;
}
extern "C" DWORD WINAPI ZH_XInputSetState(DWORD index,XINPUT_VIBRATION* vibration) {
    static auto function=reinterpret_cast<decltype(&XInputSetState)>(GetProcAddress(systemXinput(),"XInputSetState"));
    return function?function(index,vibration):ERROR_DEVICE_NOT_CONNECTED;
}
extern "C" DWORD WINAPI ZH_XInputGetCapabilities(DWORD index,DWORD flags,XINPUT_CAPABILITIES* capabilities) {
    static auto function=reinterpret_cast<decltype(&XInputGetCapabilities)>(GetProcAddress(systemXinput(),"XInputGetCapabilities"));
    return function?function(index,flags,capabilities):ERROR_DEVICE_NOT_CONNECTED;
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID) {
    if(reason==DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
        game=reinterpret_cast<BYTE*>(GetModuleHandleW(nullptr));
        GetModuleFileNameW(nullptr,logPath,32768);
        auto slash=wcsrchr(logPath,L'\\');
        if(!slash || _wcsicmp(slash+1,L"RoadRash95.exe"))return TRUE;
        wcscpy_s(slash+1,32768-static_cast<size_t>(slash+1-logPath),L"RoadRashZH.log");
        active=initialize();
        if(!active)log("Unrecognized game structure; text hooks not enabled; system XInput forwarding remains active");
    }
    return TRUE;
}
