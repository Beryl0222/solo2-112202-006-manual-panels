# 班长看板（新包版本 K2）

## 待处理译段
- feed/full [pt] （未提交）——missing-submission，受影响型号：H1、H2
- feed/hold [es] 等料，随后继续送料——no-usable-variant，受影响型号：H1
  - H1 退 'Espere material'：行宽放不下：15 列超过 H1 的 14 列
  - H1 退 'Espere. Siga'：与工位确认键名 Siga 冲突：本屏方向是 wait，值班员会照键名按错
- feed/next [es] 确认清仓以后可继续——no-usable-variant，受影响型号：H1、H2
  - H1 退 'Tras vaciar, siga'：字形放不下：第 11 位 ',' 超出 H1 字形；行宽放不下：17 列超过 H1 的 14 列；与工位确认键名 Siga 冲突：本屏方向是 conditional-proceed，值班员会照键名按错
  - H2 退 'Tras vaciar, siga'：字形放不下：第 11 位 ',' 超出 H2 字形；行宽放不下：17 列超过 H2 的 16 列；与工位确认键名 Siga 冲突：本屏方向是 conditional-proceed，值班员会照键名按错
  - H1 退 'Confirmar vaciado'：行宽放不下：17 列超过 H1 的 14 列；丢失方向：需要 conditional-proceed；丢失步骤：proceed
  - H2 退 'Confirmar vaciado'：行宽放不下：17 列超过 H2 的 16 列；丢失方向：需要 conditional-proceed；丢失步骤：proceed
- feed/next [pt] （未提交）——missing-submission，受影响型号：H1、H2

## 每款机器现在能领哪个包
- D1（西装 H1 [es]，已领未装）：整包未齐，暂无可领包；处置：recall
  - 当前面板 feed 组版本无记录可查，并置前需现场读屏
  - 已领未装的 K1 可整包撤回，待译段齐后重发
- D2（西装 H2 [es]，装好）：shared 组 K2；处置：field-correction
  - 已装机台撤不回，安排现场纠正换入可发组；记录须写明现装版本加待纠正，不得记成仍用旧译
  - 并置unrecorded：feed K1 的 next 屏无已装记录，并置前需现场读屏
  - 并置unrecorded：feed K1 的 hold 屏无已装记录，并置前需现场读屏
  - 并置key-collision：'No siga' 含确认键名 'Siga'，与共享按键说明并置时需读屏确认
  - 并置key-collision：'Siga' 含确认键名 'Siga'，与共享按键说明并置时需读屏确认
- D3（东装 H2 [pt]，未领）：shared 组 K2；处置：issue
  - 拟并置组合不在已确认读屏记录范围内，需补读屏确认
  - 并置unrecorded：feed K0 的 run 屏无已装记录，并置前需现场读屏
  - 并置unrecorded：feed K0 的 next 屏无已装记录，并置前需现场读屏
  - 并置unrecorded：feed K0 的 full 屏无已装记录，并置前需现场读屏
- D4（东装 H2 [pt]，读屏记录）：shared 组 K2；处置：hold
  - 拟并置组合不在已确认读屏记录范围内，需补读屏确认
  - 读屏记录只适用于确切并置组合，换入新组即失效；建议维持已确认组合或换后重读屏
  - 并置unrecorded：feed K0 的 run 屏无已装记录，并置前需现场读屏
  - 并置unrecorded：feed K0 的 next 屏无已装记录，并置前需现场读屏
  - 并置unrecorded：feed K0 的 full 屏无已装记录，并置前需现场读屏

## 安装后发现冲突时的回退目标
- D1：无已确认组合，需现场读屏后才能定回退目标
- D2：无已确认组合，需现场读屏后才能定回退目标
- D3：恢复 feed K0、shared K0（经确认可共存）
- D4：恢复 feed K0、shared K0（经确认可共存）
