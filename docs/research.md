# 本作语境与审校依据

研究日期：2026-11-10。对象限定为 1996 Windows PC《Road Rash》及 2026 周年版。本文区分原文直接证据、官方说明和未核实推断；实机结果另列，阅读资源不代表画面验证通过。

## 一手资料

- 本机原版备份 `TEXT/ENU.DLL`：1372 个非空字符串；0—993 为菜单/对白等主体，1000—1361 为开场与制作署名，2000—2011 为夺冠结束文本，4000—4003 为身高体重格式。完整逐条对照见 `translation-review.json`。
- 本机原版 `RoadRash95.exe`：导入表、资源与反汇编，用于核对格式化、姓名读取、字体、资源路径和补丁冲突。它不是游戏 C++ 源码。补丁 C++ 源码与游戏源码须区分。
- 游戏随附 `EXTRAS/Road_Rash_Manual.pdf`：扫描版折页说明书，提取的五页内容大量重复，不能当作五份独立证据。可与[说明书入口](https://oldgamesdownload.com/manual/road-rash-windows-manual-english/)对照。下文依据说明书实际章节标题，不虚构页码。
- 随附周年版 Credits、Controller Setup and Mappings 两份 PDF：周年版导演 Jim Vessella、技术总监 Brian Barnes；手柄设置文档要求先连接再启动。文档中 PlayStation 表部分沿用 Xbox 标签，不能据此说 PS 实体按键印有 A/B/X/Y。
- [EA 周年版页面](https://www.ea.com/games/road-rash/road-rash-30th-anniversary-edition)、[EA 发行介绍](https://www.ea.com/news/ea-classics-launch)、[EA 开发回顾](https://www.ea.com/news/from-the-vault-to-your-library)、[Steam 商店](https://store.steampowered.com/app/2448570/Road_Rash_30th_Anniversary_Edition/)：这是 PC 原作的再发行；重新授权原声、修复影片、控制器、窗口支持和最高60帧属于周年版内容。商店说明有25场赛事（5级×5赛道）、LAN及云存档。这里只是官方功能说明，不是本补丁对这些功能的测试结论。

原版资源署名明确区分 Papyrus 的 PC 开发团队与作为基础的 3DO 团队。PC 程序名单包括 Satish Bhatti、Sam Black、Rich Clark、Eric Patacchiola；不能将所有系列作品都归给同一团队。周年版重新取得PC源码、数字化原始影片材料的开发背景，来自 EA 的回顾；不推测未公开的翻译意图。

## 玩法与术语

| 原文 | 本补丁用语/判断 | 依据 |
|---|---|---|
| Thrash Mode | 街机模式；直接选赛道，省去人物选择、车行与闲聊 | ID2—3，说明书 Thrash Mode |
| Big Game Mode | 生涯模式；选角色，用比赛奖金购车，逐级竞争 | ID4—5，说明书 Big Game |
| Mano-à-Mano | 联机对战；连接方式与多人状态须按本版菜单保留 | ID13—14、288—312及联机菜单；不照搬说明书把西语说成拉丁语的玩笑 |
| Qualified | 达标；前三名达标，本级五条赛道全部达标后晋级 | 说明书 Current Position、Player Level；ID181、193、196、200 |
| Cash | 现金 | ID29、人物介绍及车行交易 |
| Trade / Trade-In | 旧车折价；不是商家优惠 | ID30、车行换购调用，金额计算实测另记 |
| Cash + Trade-In | 现金加旧车折价，供换购使用的总额 | 不把它当作账户现金；不得为适配显示修改资金 |
| Wrecked / Totalled | 撞坏 / 报废；不能混成同一种失败结算 | ID176、182、192—194、374；说明书 Damage Gauge |
| Busted / fine | 被捕 / 罚款；对白里的 bail 保留“保释金”口吻 | ID177、195—198、543；不把对白当现实法律建议 |
| Damage / Stamina | 车辆损坏与骑手体力分别处理 | 说明书 Racing/Fighting；体力耗尽会摔下车 |
| Nitro | 氮气加速；说明书描述装有系统的车每场十次 | 原文实际写 nitrous oxide；保留玩家熟悉的“氮气”，不声称化学成分是氮气 |
| Race / Biker Resolution | 比赛分辨率 / 车手分辨率 | 说明书 Graphics；车手是预制图像而非替换3D人物模型 |
| Restroom | 洗手间 | 说明书 Restroom Options、游戏厕所画面、ID6；设置功能不改变地点含义 |
| Schmooze | 闲聊 | 说明书 Schmooze、ID52—53；包括赛道建议和关系变化 |
| Save / Save As | 保存到当前档 / 另存新档 | ID64—69、说明书 Save Game；不修改玩家昵称或存档字段 |

维修等待与坐牢都可能丢失本级赛道达标记录（ID193、196）；付不起费用会结束游戏（ID198）。这不是泛化成扣钱后无条件继续。车行按破旧、运动、超级摩托分级（58—63）；虚构品牌及型号不能擅自对应到现实厂商。保留 Banzai/万岁、DMG、ZYX 等现有合理命名，不迎合个人审美重命名。

## 叙事和人物

本作的文本证据支持人物简介、赛场行为、俱乐部对白及胜负/被捕影片构成的碎片化叙事；未发现足以编成一条完整线性剧情的文本。赛季结局 ID2001—2011 是夺冠后大家暂忘恩怨、举杯，主角幻想代言与电视电影带来的财富，并嘲讽短暂成名。不要把幻想写成已发生的真实收入。

| 角色 | 已有译名保留 | 直接依据与口吻 |
|---|---|---|
| Axle | 阿克塞尔 | ID40 冷酷坏小子；506—517等多火力、铁链、动作片夸张威胁。ID700/701叙说父亲与偷弹珠机硬币；不添加童年细节。 |
| Bose Jefferson | 博斯·杰斐逊 | ID41 随和但拳重；518—529等先讲规矩再警告；911以第三人称说自己。808/813提洛杉矶。 |
| Cydney Bass | 辛迪·巴斯 | ID42富家娇女；530—541钱、优越感和威胁并存；724/729提阿克伦。Bass与鲈鱼双关在598/775/790有直接用词。 |
| Milwaukee Jon | 密尔沃基·乔恩 | ID43前科犯、冒险骑法；542—553粗粝警告；736/741提坐牢，832/837提威斯康星。 |
| Pearl McKurdy | 珀尔·麦柯迪 | ID44复古朋克、无政府态度；554明确称Axle为男友，562称灵魂伴侣；748提父母从莫西干头转向华尔街。不是所有挑衅对象都是固定仇人。 |
| Rhonda the Rash | 疯婆罗达 | ID45前纽约客；568下东区、572/764与Mike亲密及暴力关系，956互殴不记仇；保留凶悍直白语气，不添加额外辱骂。 |
| Slim Jim | 瘦子吉姆 | ID46辍学、班级活宝与英年早逝票选；578等战术务实、583木刺暗示棍棒。Slim为描述性绰号。 |
| Teflon Mike | 铁氟龙迈克 | ID47幼时头伤、不可预测；590等喜欢交手；971/973/862“不粘/粘住”直接构成Teflon双关。译名没有确定错误，保留。 |

普通对手320—349与警察350—356只有姓名，不给他们杜撰生平。357原文是单点，须单独追踪用途，不能直接当作警察丢名字的证据。车行Olley的说明书叙述为退下来的车手开店提供建议，不把每句菜单帮助都认定为他本人台词。

## 俚语与文化核对

- **schmooze**：不是调查或谈判。现译“闲聊”与说明书功能一致。[Merriam-Webster](https://www.merriam-webster.com/dictionary/schmooze)解释非正式聊天；[语言学者Diana Boxer的历史说明](https://archive.news.ufl.edu/articles/2006/01/the-etymology-of-schmooze.html)记早期书证到1897。不能用今天商业社交的单一含义套回本作。
- **gonzo**（47）：疯狂、离奇、极端，非特定新闻记者身份。[Merriam-Webster](https://www.merriam-webster.com/dictionary/gonzo)的词史列1971；[Collins](https://www.collinsdictionary.com/us/dictionary/english/gonzo)给1970—75及非理性/荒诞义。保留“狂人”，将brain damaged准确接回头伤。
- **Milktoast Mike**（670）：怯懦软弱的挖苦，现译“怂包迈克”可保留。[词源记录](https://www.etymonline.com/word/milquetoast)追溯漫画人物及1930年代用法；不是牛奶吐司的字面称呼。
- **Teflon**：不粘材料品牌及“指责难以附着”的引申义。[Oxford](https://www.oxfordlearnersdictionaries.com/us/definition/english/teflontm_2)记录形容词用法。本作是否特指某位政治人物无证据，不添加典故。yellow punk在862是胆小鬼，修正“黄胆怂包”。
- **squid**（689/696/822/899）：对缺乏本事车手的蔑称，结合原文威胁和骑术语境保留“菜鸟”；尚未取得足够年代语料，不编造缩写来源。
- **club**（915/638）、**Bass**（598/775/790）、**save face**（678）、**right of way / might makes right**（703）、**number's up**（954）都可由同句或上下文核对双关。保留现有表达，不给每个笑话塞说明性长译注。
- **a death wish**（43）通过敢死骑法夸张，不足以确认为自杀愿望；**reach puberty**（961）是进入青春期，不是度过青春期；**scrub pavement out of you**（511）是从伤者身上清除路面碎屑，原译把对象倒置。这些改动有句内证据。
- 153 socket-popping、575 fly boy、826 blow/bite、歌曲Pansy的精确双关仍有不确定性，保留现有译文并列入B类；不拼凑历史出处。
- 游戏中加州地点、911、四车道、酒吧、朋克发型、电视脱口秀、超市收银台小报均依实际文本解释。说明书The City缆车描写暗指旧金山，但菜单仍叫“都市”，不擅自把显示名改成旧金山。比赛和对白夸张不能当真实社会统计。
- 225—230的六支乐队保留英文供辨识；241—254歌名现译作为参考译名，不声称官方中文名称，不借歌词推测作者意图。1991—1994的录音署名在原始资源中可查，本轮署名内容排除。周年版的授权音乐可在比赛中播放由官方商店说明确认，不能误当1996默认功能。

## 修改与保留

`translation-changes.json`逐项写出旧译、新译、分级与理由。普通人名音译、准确的战术建议及角色口吻保留。B类疑点不强行统一。`translation-review.json`覆盖所有1372个资源条目，排除项与控制字段也单独列明；显示验证另记，不能用1166条翻译或1372条资源宣称实际100%覆盖。

没有复制其他民间汉化。用户评论仅用于定位疑点，尤其“360删EXE”和“警察只显示点”不视为已复现事实。外部资料到此止于实际翻译判断，不扩展成无关历史研究。
