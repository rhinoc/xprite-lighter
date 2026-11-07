# Xprite · 有几何真值的光照 Bench v3

面向两个任务：从一张带明暗的像素图估计法线；给定同一张图和目标灯位，预测换光后的 RGB。数据来自 Kay Lousberg / KayKit 的 8 个 CC0 游戏模型，每个模型 2 个视角、4 种原生尺寸（32、48、64、96 px），共 **64 个用例**。角色包括挥剑骑士、术士、兜帽游侠、骷髅战士，道具包括宝箱、探测车、水磨坊和神龛。

这是模型投影生成的可控像素画样本。v2 的手绘素材适合观察实际画风；未提供可靠目标的样例不进入本包的准确率统计。本包 64 个视图／尺寸组合来自 8 个对象；同一模型的多个视角有相关性。

## 先看一个例子

也可以直接在 Xprite 打开 projects/rover-64.aseprite；两个帧对应两个视角，7 个图层分别显示输入、底色、预测法线、GT 法线和换光对照。

打开 `overview.png` 或 `gt-comparison.gif`。预览中，Xprite 用 `input.png` 估法线。为了**单独观察法线差异**，两列均用已知的同一份底色和同一盏灯重渲染。每个用例（例如 `cases/rover-a-64/`）包括：

| 文件 | 来源与用途 |
|---|---|
| `input.png` | 从左上方照亮、分成五档明暗的单张彩色 RGBA。给被测算法的输入。 |
| `gt/normal.npy` | 每个可见像素的 float32 单位着色法线（模型顶点法线经可见三角形内插和相机变换），形状 H×W×3。用于角度误差。 |
| `gt/normal.png` | 同一法线编码为 8 位 RGBA，方便导入编辑器。+X 右，+Y 上，+Z 朝观察者；法线 RGB 数据不作 sRGB 线性化。 |
| `gt/albedo.png`、`gt/mask.png` | 基准材质的未受测试光照的底色、可见像素遮罩。颜色从模型底色纹理／材质取得；作为受控渲染的漫反射底色使用。 |
| `gt/geometry.npz`、`gt/camera.json` | 相机深度、实际命中的三角形 ID、平面几何法线和可重现的正交相机参数。法线估计默认评分目标是着色法线。 |
| `gt/cel-{right,top,bottom,front}.png` | 四个新灯位的独立目标 RGB，与输入同画风。端到端换光评估比对这些图。 |
| `gt/smooth-{right,top,bottom,front}.png` | 相同几何和灯位的连续漫反射参考。用于测出法线估错对最终着色的影响。 |

所有输入、法线和目标共用同一几何、视角和像素中心采样。仪器是确定性的正交光栅化，逐像素深度测试选择可见三角形。没有抗锯齿或空间混合。GT 用确定的白色方向光在线性颜色空间计算；不模拟场景投影、多次反射、金属高光或透射。火把等发光外观在本包均按漫反射材质处理。

## 跑哪项，算法能看见什么

1. **法线估计。** 算法只看 `input.png`，输出 `pred/<case-id>.png`（8 位 RGBA，alpha 同输入），或原始 float 数组 `pred/<case-id>.npy`。仅可见前景计分，报告平均角误差、各视图的 P95 和 22.5° 内比例。
2. **已知底色的着色诊断。** 评分器把预测法线与 GT 底色一起送进统一光照模型，在 4 个新灯位比较连续光照的 RGB MAE。这里刻意提供底色来隔离法线质量，不代表算法能从原图找回底色。
3. **单张图端到端换光。** 算法可读取输入 RGBA 和注明的原灯、目标灯与着色模型参数；不读取 `gt/` 内的底色、法线、深度或目标图。每例交 4 张图 `relit/<case-id>/{right,top,bottom,front}.png`。按可见前景计算 8 位 sRGB 通道的 MAE，越低越好。
4. 先逐例、逐对象取均值，再对 8 个模型等权平均。不要将该值解释成独立的 64 个角色，也不要据此推论在手绘角色上的等量提升。

## 本次结果

Xprite 提交 `54d8133ca975a47518c7ec979de32ce9591f2ad4`，所有模型固定 Object 默认预设，无按样例调参。端到端基线取 Xprite 预测法线，将已经带原光的输入图直接当底色，用 bench 的五档方向光重新着色。这是明确定义的比较流程；编辑器的默认点灯不是本次的渲染器。

| 指标 | Xprite 基线 | 朴素对照 | GT 自检 |
|---|---:|---:|---:|
| 法线平均角误差 | 40.47° | 45.99°（全部朝正面） | 0° |
| 法线在 22.5° 以内 | 18.56% | 10.14% | 100% |
| GT 底色＋各自法线，连续光照 RGB MAE | 18.22/255 | 20.94/255（全部朝正面） | 0 |
| 单图端到端换光，五档 RGB MAE | 29.81/255 | 29.87/255（直接复制输入） | 0 |

每例数字和每个模型的汇总分别存于 `baseline/metrics/per-case.csv` 与 `baseline/metrics/summary.json`，对照结果在 `checks/`。64 例的 512 张目标 RGB 均已逐像素复现，解析平面、遮挡关系、镜像／非均匀缩放法线、蒙皮及颜色编码也有独立测试。

## 独立公开数据复核

`external/external-benchmark.json` 保存 DmytroKhitro/pixel-art-normal-maps 项目作者评估列表里的 274 张 32×32 样本及分数，共 185 个模型 ID。与原始数据文件按文件名匹配，逐张核对了前景像素数（合计 67,403）。作者使用图像级验证划分。Xprite Object / Character 实跑结果分别 **41.13° / 40.77°**；同样本上作者发布的 EDT Bevel / U-Net 分别为 **37.00° / 32.16°**。后两者引用原项目 CSV。保留同一坐标编码与指标，未调参。公开目标经法线分量量化和轮廓处理，是风格化法线；其成绩与本包未量化网格法线分开报告。

原数据集共 14,497 对图像，包含 648 个模型。数据卡标注 CC BY 4.0，原模型还各有许可。这里只附逐例指标和来源，不复制该数据集的美术文件。[数据卡](https://huggingface.co/datasets/DmytroKhitro/pixel-art-normal-maps) · [原作者代码与逐图基准](https://github.com/Dmiktor/pixel-art-normal-maps)

## 自己运行

需要 Python、NumPy、Pillow。评分器会检查尺寸、前景数值与 alpha。目录以解压后的根目录为准。

```sh
python -m pip install numpy pillow
python tools/score.py --dataset . --normals predictions --report run/metrics-normal
python tools/score.py --dataset . --relit relit --report run/metrics-relit

# 从随附的 8 个模型重建全部输入与目标
python tools/build.py --dataset .
python tools/test_raster.py
python tools/check.py --dataset .

# 对指定 Xprite 本地 checkout 运行真实生成器（适配器已通过 Node 24.22.1 验证）
python tools/baseline.py --dataset . --repo /path/to/xprite --out new-run
```

## 作者与来源

随包静态模型来自 **Kay Lousberg / KayKit，CC0 1.0**。角色按作者动画选定时刻冻结，选择不冲突的武器和装备。每个角色的上游 URL、提交号、原始哈希、动画时刻和保留节点，以及每个道具的原始模型和打包信息，均在 `sources/models.json`；各包作者许可也在该目录中。`models/` 内的静态 GLB 可以直接重建本包。公开验证集的署名与许可另见上节。

