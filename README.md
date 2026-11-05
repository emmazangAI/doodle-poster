# 照片涂鸦小人海报

把一张照片，做成一张白底海报：照片里的东西原样保留，旁边写一句手写体的短话，周围画四五个黑色线稿小人。

**全程在本机算，不需要 AI 生成图片。** 几秒钟出图，不满意改两个数字再来一次。

## 为什么不用 AI 生图

文字生图的模型拿不到你那张照片，只能凭描述"想象"一道菜，出来的不是你的。

这个工具换了个做法：东西直接从照片里抠出来（保真），小人用代码画（可控）。少了点手绘的松弛感，换来的是——想改哪里就改哪里，不用抽卡。

## 电脑上需要什么

- macOS 14 或更新（抠图用的是系统自带能力）
- Python 3.9 以上，装两个库：`pillow`、`numpy`
- Xcode 命令行工具（第一次运行会自动编译一个小工具）

## 装

```bash
mkdir -p ~/.codebuddy/skills
git clone https://github.com/emmazangAI/photo-doodle-people-poster.git \
  ~/.codebuddy/skills/photo-doodle-people-poster
```

放进 skills 目录后，`SKILL.md` 里写了完整用法，AI 会自己读。

## 用

先看一眼抠出来是什么样，顺便拿到主体的位置：

```bash
python3 scripts/compose.py --image 照片.jpg --out probe.jpg --print-bbox
```

然后写好小人的 JSON，正式出图：

```bash
python3 scripts/compose.py --image 照片.jpg --figures 小人.json --out 海报.jpg
```

只想加一句话、不画小人，一条命令就够：

```bash
python3 scripts/compose.py --image 照片.heic --text "先来一块" --out 海报.jpg
```

## 能调的参数

| 参数 | 默认 | 干什么 |
| --- | --- | --- |
| `--image` | 必填 | 照片，HEIC 可以直接给 |
| `--out` | 必填 | 存到哪 |
| `--figures` | 不给也行 | 小人和短句的 JSON |
| `--ratio` | `3:4` | 也能选 `4:5`、`1:1`、`9:16`、`2:3` |
| `--subject-y` | `0.50` | 主体在图上的高低 |
| `--subject-w` | 自动 | 主体占多宽 |
| `--text` | 不给也行 | 短句，2 到 5 个字 |
| `--text-size` | 图高 ×0.077 | 字多大 |
| `--font` | 自动 | 自动找手写字体 |
| `--erase` | 不给也行 | 擦掉入镜的手、餐具，能擦好几块 |
| `--seed` | `7` | 换个数，笔触变个样 |
| `--print-bbox` | 关 | 只打印主体位置 |

## 小人怎么摆

小人不是选模板，是每张照片现写坐标：站在哪、手伸到哪、脚踩在哪。完整写法见 [`references/figure-json.md`](references/figure-json.md)。

```json
{
  "hip": [0.145, 0.792],
  "scale": 2.0,
  "hands": [[0.126, 0.716], [0.166, 0.716]],
  "feet":  [[0.111, 0.832], [0.180, 0.834]]
}
```

两条踩过的坑：

- `hip` 是屁股的位置，不是脚底。脚的纵坐标大概写"屁股 + 0.04"，写远了腿会变蜘蛛腿。
- 黑色的东西上，黑线小人会看不见。把小人放在白底或者浅色部位，别加白边。

## 干不了的事

- 小人是线条画的，干净，但不"松"，跟生图模型的手绘感不是一回事。
- 透明、反光、跟背景同色的东西，抠不干净。
- 手写字体用的是 macOS 自带字体，别的系统得自己指定一个字体文件。

## 许可

MIT
