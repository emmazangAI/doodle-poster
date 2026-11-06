# doodle-poster（照片涂鸦小人海报）

把一张真实照片做成 **白底 + 手写短句 + 黑色涂鸦小人** 的海报，**全程本地渲染，不需要任何图像生成模型**。

适合在 coding agent 环境里用：给一张图，几秒钟出图，不满意改几个坐标再跑一次。

```
照片  →  Vision 抠图  →  白底柔影  →  手写字体短句 + 箭头  →  代码绘制的涂鸦小人
```

## 为什么不用生图模型

文生图模型拿不到你的原图，只能用文字"想象"一道菜；参考图编辑模型能做到，但很多环境里没有。

这个工具换了个思路：主体直接抠原图（保真），小人用代码画（可控）。牺牲一点手绘的松弛感，换来确定性和可迭代。

## 环境要求

- macOS 14+（抠图用 Vision 框架）
- Python 3.9+：`pillow`，`numpy`（缺 numpy 时跳过字体形变，仍可用）
- Xcode Command Line Tools（首次运行自动编译 `swiftc` 抠图工具）

## 安装

```bash
mkdir -p ~/.codebuddy/skills
git clone https://github.com/emmazangAI/doodle-poster.git ~/.codebuddy/skills/doodle-poster
```

作为 CodeBuddy / Claude 风格的 skill 使用时，把目录放在 skills 路径下即可，`SKILL.md` 里有完整工作流。

## 用法

```bash
# 1) 先拿到主体真实轮廓（每 5% 高度的左右边界），坐标不用猜
python3 scripts/compose.py --image photo.jpg --out probe.jpg --print-outline
# {"canvas": [1536, 2048], "outline": {"top": 0.202, "bottom": 0.797, "rows": [...]}}

# 2) 写 figures.json，然后正式出图
python3 scripts/compose.py --image photo.jpg --figures figs.json --out poster.jpg
```

最短的一次调用：

```bash
python3 scripts/compose.py --image photo.heic --text "先来一块" --out poster.jpg
```

### 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--image` | 必填 | 照片，支持 HEIC |
| `--out` | 必填 | 输出路径，`.jpg` 会同时存一份 PNG |
| `--figures` | 无 | JSON 文件或内联 JSON |
| `--ratio` | `3:4` | `3:4` `4:5` `1:1` `9:16` `2:3` |
| `--subject-y` | `0.50` | 主体中心纵向位置 |
| `--subject-w` | 自动 | 主体宽度占比，宽扁主体自动取 1.0 |
| `--text` | 无 | 文案，2–5 个汉字 |
| `--text-size` | 画布高 ×0.077 | 字号 |
| `--font` | 自动 | 自动找系统手写体，找不到退回黑体并做形变 |
| `--erase` | 无 | 擦掉入镜的手、餐具等，可重复；矩形 `x0,y0,x1,y1`，多边形 `x0,y0 x1,y1 ...` |
| `--erase-feather` | `0.006` | 擦除边缘羽化，避免直角白缺口 |
| `--mend-band` | `0`（关） | （实验）对照片画幅裁断的主体边做渐隐，宽度按主体尺寸占比 |
| `--seed` | `7` | 笔画抖动种子 |
| `--print-bbox` | 关 | 只打印主体包围盒 |
| `--print-outline` | 关 | 打印主体轮廓剖面 |

## 小人怎么写

小人不是选模板，是每一张照片现写坐标：髋点在哪、手伸到哪个位置、脚踩在哪。手的位置加 `"snap": "hands"`，运行时会被吸附到主体真实轮廓上，并画出扣住边缘的小爪。完整规格见 [`references/figure-json.md`](references/figure-json.md)。

```json
{
  "hip": [0.145, 0.792],
  "scale": 2.0,
  "hands": [[0.126, 0.716], [0.166, 0.716]],
  "feet":  [[0.111, 0.832], [0.180, 0.834]]
}
```

两条经验：

- `hip` 是髋点，不是脚底；一条腿约 `40 × scale` 像素，脚写太远会变成蜘蛛腿。
- 深色主体上黑色线条会消失。把小人放在白底或浅色部位，不要给小人物加白描边。

## 已知限制

- 小人由几何线条绘制，干净但不"松"，比不上生图模型的手绘质感。
- Vision 抠图对透明、高反光、与背景同色的主体容易失败。
- 手写字体依赖 macOS 自带字体；其他系统请用 `--font` 指定一个手写字体文件。

## 许可

MIT
