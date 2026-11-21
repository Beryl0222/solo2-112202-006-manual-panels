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
