# 银龄智伴 · AI 家庭养老陪护平台

银龄智伴把药盒照片、手动健康记录和日常活动沉淀为本地档案，再按问题筛选相关信息交给千问生成建议。建议可以继续转成提醒、完成记录或家属跟进，形成“记录—分析—行动”的照护闭环。

## 参赛信息

- 学校：广东科贸职业学院
- 队伍名称：个人参赛
- 队员：林伟健
- 指导老师：无

## 本地启动

```bash
./start.sh
```

打开 <http://127.0.0.1:4173/>。如果没有配置千问 Key，网站仍可使用本地演示回答；配置 `DASHSCOPE_API_KEY` 后，页面会显示千问实时回答。Key 只在后端环境变量中读取。

如果端口 4173 已被占用，请先关闭旧的 `server.py` 进程，再重新运行启动脚本。

## 提交前检查

```bash
python3 check_submission.py
```

检查脚本只做语法、数据结构、网页文案和本地接口检查，不会修改档案。

## 竞赛演示前

```bash
python3 reset_demo.py
./start.sh
```

首次打开是空的真实档案。点击“查看演示数据”可以进入预置的王阿姨案例；退出后回到本地真实档案。

3 分钟现场讲解稿见 [PRESENTATION.md](PRESENTATION.md)，7 分钟视频演示稿见 [VIDEO_SCRIPT_7MIN.md](VIDEO_SCRIPT_7MIN.md)，技术文档 PDF 草稿见 [TECHNICAL_DOCUMENT.md](TECHNICAL_DOCUMENT.md)，提交清单见 [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md)。

阿里云 ECS 部署模板和操作步骤见 [DEPLOY_ALIYUN.md](DEPLOY_ALIYUN.md)。

建议演示顺序：

1. 展示空档案和演示数据切换。
2. 在健康档案中录入血压或活动，并设置提醒。
3. 询问“我今天适合出去散步吗？”。
4. 展示回答下方的“本次建议依据”。
5. 点击“生成提醒”或“标记已完成”。
6. 从首页快捷服务进入“问问 AI”或“设置提醒”，再删除一条待办并刷新页面，证明状态已经保存。

## 数据和安全

- `elder_profile.json` 是本地真实档案；`demo_profile.json` 是评委演示档案。
- API Key 只在 `server.py` 后端读取，不会发送到前端。
- 只有与当前问题相关的档案字段会发送给千问。
- AI 不诊断、不改药；不确定的识别结果会标记为“待确认”。
- `reset_demo.py` 清空真实档案，并清除演示流程中临时新增的记录、任务和删除状态，保留预置案例。
