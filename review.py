# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Record the 2026-11-10 manual English/Chinese review; no game writes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Changes selected after reading every resource entry, the supplied manual,
# character bios, all 480 club lines, and the reported game screenshots.
CHANGES = {
    6: ('洗手间', 'A', '官方说明书 Restroom Options、厕所场景；不是休息室。'),
    30: ('旧车折价', 'A', '车行出售旧车抵扣购车价格，避免与普通优惠折扣混淆。'),
    43: ('身高：%s\n体重：%s\n座驾：%s\n现金：$%d\n不要命的前科犯。乔恩那股玩命的骑法，连老车手见了都发怵。', 'A', 'death wish 在冒险骑法语境中夸张指不顾危险；一心求死误成明确自杀意图。'),
    47: ('身高：%s\n体重：%s\n座驾：%s\n现金：$%d\n迈克小时候摔伤了脑袋，是个天不怕地不怕、谁也摸不透的狂人，脑子也确实摔坏了。', 'A', 'brain damaged 与幼年头伤直接呼应，不能含混写成精神疾病。'),
    157: ('转向迅捷，配有氮气，但车架容不得半点失误，高速时很难稳住行车路线。\n$%d\n100马力/430磅\n操控：闪电般\n加速：撕裂肌肉\n极速：令人胆寒', 'C-润色', '保留原参数与夸张口吻；unforgiving frame 不直译为毫不宽容。'),
    270: ('Delete', 'A', '此处是实体按键名，须与键盘标识一致；224 的删除命令保持中文。'),
    289: ('创建房间', 'A', '联机功能动词 Host 是创建/主持游戏，不是一般主持活动。'),
    295: ('创建联机房间。选择等级、连接方式和角色，再等朋友加入！', 'C-润色', '与289一致，不改变连接功能。'),
    397: ('可选标准车手图像，或占用更多内存的高清车手图像。', 'A', '原版车手采用预制图像；高分辨率选项不是更换3D模型。'),
    511: ('我要把你揍得满身嵌进柏油渣，得靠人一点点刷出来。', 'A', 'scrub the pavement out of you：清除嵌入身体的路面碎屑，旧译反转了清理对象。'),
    606: ('都说人总伤害自己爱的人。你就例外了——不爱你也照揍。', 'A', '敌对威胁句中的例外是打不爱的人；原译容易被理解为不伤害对方。'),
    667: ('你也不过是个输家，被我一路狂怒着甩在身后。', 'C-润色', 'in my wake 指身后留下的结果，保留狂怒意象，消除生硬尾流搭配。'),
    802: ('珀尔，要用一个词表达我对你的感觉，那就是“你让我恶心”。', 'A', '原文说一个词却给出整句，保留故意自相矛盾的笑点。'),
    862: ('铁氟龙，我要让“胆小鬼”的名声牢牢黏在你身上。', 'A', 'yellow 此处指怯懦；保留 Teflon / stick 的不粘双关，删除生硬的黄胆。'),
    917: ('我就没见过骑得像你这么糙的。想冲到车群前面，打架最好够厉害。', 'C-润色', 'crude rider 指骑术粗糙，改掉最粗糙的车手这一生硬搭配。'),
    924: ('我就没见过骑得像你这么糙的。想冲到车群前面，打架最好够厉害。', 'C-润色', '与917同一原文统一。'),
    961: ('瘦子，变声了吗？等进了青春期再来吧。', 'A', 'reach puberty 是进入青春期，旧译过了青春期改变时间条件。'),
    982: ('辛迪，你是不是拿额头砸空易拉罐砸多了？没人敢这么惹我。', 'A', '酒吧语境的 empties 是空饮料罐，不是罐头食品。'),
    987: ('放大修复影片', 'A', 'upscaled 明确为放大处理；不将其描述成原生高清。'),
    2002: ('-大家一时忘乎所以，', 'C-润色', 'temporary insanity 为夺冠后一时失态；不是短暂狂欢这件事本身。'),
    2011: ('-成名只有十五分钟。掐着表享受吧。', 'C-润色', '保留短暂成名与 Count em 的戏谑，不补写现实代言收入。'),
}
DOUBTS = {
    37: 'Rash 有鲁莽及系列名双关；疯婆符合45及568台词，但不冒充官方定译。',
    39: 'Teflon 有不粘引申义，971/973/862直接呼应；保留现有铁氟龙音译。',
    115: 'Pico 为虚构车型名，西语可有峰/尖等义；没有证据定为某一地名。',
    153: 'socket-popping 可指关节/眼眶的夸张；暂保留眼球出眶，不凭猜测改为肩膀脱臼。',
    243: '原文 Dinosaur Vacume 的拼写照录；歌曲中文非官方译名，不推测歌词含义。',
    244: 'Pansy 是歌曲名且有多义；没有以歌词/作者解释确定标题意图，保留现译。',
    432: '帮助文本仍描述旧版画框影片，周年版选项含upscaled；须按实际运行功能判断，暂保留。',
    575: 'fly boy 可能含风流少年与苍蝇外形双关，未确认历史语料和具体语气，暂保留。',
    826: 'blow/bite 改写 bark/bite 且可能含性暗示；缺乏作者说明，保留含混而不放大。',
}

def context(i):
    if 506 <= i <= 985:
        chars = ['阿克塞尔','博斯','辛迪','乔恩','珀尔','罗达','吉姆','迈克']
        return f'俱乐部对白；资源组推断第{(i-506)//96+1}级，{chars[((i-506)%96)//12]}（运行触发另验）'
    if 320 <= i <= 349: return '普通比赛对手姓名'
    if 350 <= i <= 357: return '警察姓名/占位'
    if 358 <= i <= 365: return '主要角色短名；须保护立绘文件标识'
    if 32 <= i <= 47: return '角色选择/人物介绍'
    if 96 <= i <= 158: return '车辆品牌、型号、性能与介绍'
    if 2000 <= i <= 2011: return '赛季夺冠结束文本'
    if i >= 4000: return '身高体重格式'
    if 1000 <= i <= 1361 or i in (175,381): return '开场/制作人员/署名（本轮排除）'
    if 241 <= i <= 254: return '点唱机歌曲标题（中文为参考译名）'
    if 443 <= i <= 495: return '音频、网络及拨号错误/状态'
    return '菜单、游戏状态或功能说明；具体显示见覆盖清单'

def main():
    english = json.loads((ROOT/'data/english-strings.json').read_text(encoding='utf-8'))
    old = json.loads((ROOT/'data/previous-translations.json').read_text(encoding='utf-8'))
    current = dict(old)
    for i,(new,grade,reason) in CHANGES.items(): current[str(i)] = new
    (ROOT/'translations.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows=[]
    for key,en in english.items():
        i=int(key); prev=old.get(key,en); new=current.get(key,en)
        excluded=1000<=i<=1361 or i in (175,381)
        technical=en in ('*','.',':','+','-') or i in (0,2000,4000,4002)
        grade='排除' if excluded else '技术字段' if technical else 'C-保留' if key in old else '合理保留英文'
        reason=('本轮明确排除；已有文本不作语义改写。' if excluded else '占位/控制/格式字段，不应为提高汉化数而改写。' if technical else
                '逐条核对英文与同组语境后保留；未发现可确定的语义错误。' if key in old else '按键标识、协议、品牌或乐队名称，保留原文便于辨识。')
        if i in DOUBTS: grade='B-保留待核';reason=DOUBTS[i]
        if i == 357:
            grade='技术字段-原样保留'
            reason='原版警察名称表第8项指向357；生成/轮换路径416c32、417067会读取此项。用户明确要求占位符保持原样，不改名、不改变索引。'
        if i in CHANGES: new,grade,reason=CHANGES[i]
        rows.append(dict(id=i,english=en,previous=prev,chinese=new,context=context(i),verdict=grade,changed=prev!=new,basis=reason,display='尚未验证；不以资源审校等同实机覆盖'))
    docs=ROOT/'docs';docs.mkdir(exist_ok=True)
    (docs/'translation-review.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (docs/'translation-changes.json').write_text(json.dumps([r for r in rows if r['changed']],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'reviewed_resources':len(rows),'changed':sum(r['changed'] for r in rows),'uncertain':len(DOUBTS)}))

if __name__=='__main__':main()
