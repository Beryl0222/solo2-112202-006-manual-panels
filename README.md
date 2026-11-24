# 多语言设备面板的短句与厂内试运行

业务资料使用虚构编号和合成叙述。文本保持来件拼写和措辞。各表是独立的来源记录。
TSV 文件采用 UTF-8，首行为列名。行首 id 是该表的稳定记录号，空格和标点属于原文，空单元格表示来件未填。
日期时间采用所在地本地时间。资料内注明为编号列表的字段用竖线分隔。

## 资料字段

- `materials/strings.tsv`。bundle 是面板逻辑页面组，screen 是稳定显示位置。variants 是译员原给出的候选，使用竖线隔开。
- `materials/hardware.tsv`。columns 是按单字符占一列的屏宽。glyphs 是现场导出的字形约束，本资料的拉丁大写、小写及空格均各占一列。
- `materials/rollouts.tsv`。phase 是领包实际状态。gloss 是当前面板对操作键的已装原文。
- `materials/installed_strings.tsv`。rev 为实际面板包版本。按面板包记录屏号、整个原词组和现场按钮文字。

## 运行资料检查

使用 CPython 3.11.2 和标准库。资料检查仅读取输入。

```sh
python3 pack_check.py
python3 -m unittest -v
```

## 编校、拼装与看板

```sh
python3 build.py            # 读 materials/，产物写入 out/
```

流程：逐屏逐机型核对译员备选（`review.py`）→ 拼页面组与机台处置
（`packages.py`）→ 班长看板（`dashboard.py`），全程事件写入可回查日志
（`journal.py`）。

- `panel_profile.py` 把 hardware.tsv 的字形、行宽、同屏可见与换包方式描述
  解释成约束；新型号带来新描述时会报错，需先登记解释规则。
- `knowledge/semantics.json` 按屏登记原句必须保住的方向、否定、步骤与动作
  对象，按备选句登记译法实际表达的语义。译员提交新备选时，未标注的句子会
  被拦下，先补标注再编校。
- 编校硬冲突：放不下（越界或无法显示的字）、保不住义、与工位共用确认键叫
  法冲突（等待/停止方向的屏带上键名，值班员转台后会照键名按错）。允许用
  下一屏补全步骤，但当前屏必须独立保留它控制的操作方向。
- 整包机型组不齐则无可领包；页面组机型可单发就绪的组，并对其余旧组做并
  置辨认检查。人工读屏记录只适用于确切包和并置版本，组合一变即失效。已
  领未装可撤回；已装只能安排现场纠正，且不得记成仍用旧译。

产物：

- `out/packages/<lang>/<hardware>.json`  分语言面板包（可交试运行的组）
- `out/reports/pending_segments.json`    待译员处理的译段、冲突与受影响型号
- `out/reports/dashboard.json` / `.md`   班长看板：待处理译段、每款机器现
  在能领哪个包、安装后发现冲突时的回退目标
- `out/journal.jsonl`                    编校与安装范围事件，可按
  kind / lang / hardware / screen 回查字形、短句歧义和安装范围

