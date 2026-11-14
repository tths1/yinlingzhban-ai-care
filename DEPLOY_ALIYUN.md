# 阿里云 ECS 部署说明

这份说明适用于当前的 Ubuntu 24.04 ECS。当前项目使用 Python 标准库，服务器不需要安装额外的 Python 依赖。对外只开放 Nginx 的 80/443，Python 服务保持在 `127.0.0.1:4173`。

## 1. 登录服务器并安装基础软件

在阿里云 Workbench 进入终端后执行：

```bash
sudo apt update
sudo apt install -y python3 nginx git unzip
```

创建项目目录（下面的 `ubuntu` 可以替换为实际登录用户）：

```bash
sudo mkdir -p /opt/yinlingzhban /etc/yinlingzhban
sudo chown -R ubuntu:ubuntu /opt/yinlingzhban
```

## 2. 上传项目

项目还没有 GitHub 远程仓库时，可以在 Workbench 的文件上传功能上传 `output/银龄智伴_省赛提交草稿.zip`，再解压：

```bash
unzip -o /tmp/银龄智伴_省赛提交草稿.zip -d /opt/yinlingzhban
```

如果之后已经创建 GitHub/Gitee 仓库，也可以改为：

```bash
git clone <仓库地址> /opt/yinlingzhban
```

确认 `/opt/yinlingzhban/server.py` 和 `/opt/yinlingzhban/dist/index.html` 存在。

## 3. 配置千问 Key

将 Key 写入服务器环境文件。下面的值只使用占位符，部署时在终端本地替换：

```bash
sudo tee /etc/yinlingzhban/yinlingzhban.env >/dev/null <<'EOF'
DASHSCOPE_API_KEY=在这里填写你的百炼APIKey
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EOF
sudo chmod 600 /etc/yinlingzhban/yinlingzhban.env
```

如果百炼 API Key 以 `sk-ws-` 开头，请把 `DASHSCOPE_BASE_URL` 改成百炼 API Key 页面显示的“按量付费 Base URL”，再重启服务。业务空间 Key 需要使用对应的专属域名。

不要把真实 Key 写进项目文件、前端页面或 Git 仓库。

## 4. 配置后台常驻运行

将 `deploy/yinlingzhban.service.template` 复制到服务器后，把其中的 `__SSH_USER__` 和 `__APP_DIR__` 替换为实际值。例如：

```bash
sudo cp /opt/yinlingzhban/deploy/yinlingzhban.service.template /etc/systemd/system/yinlingzhban.service
sudo sed -i 's/__SSH_USER__/ubuntu/g; s#__APP_DIR__#/opt/yinlingzhban#g' /etc/systemd/system/yinlingzhban.service
sudo systemctl daemon-reload
sudo systemctl enable --now yinlingzhban
sudo systemctl status yinlingzhban --no-pager
```

检查本机接口：

```bash
curl -I http://127.0.0.1:4173/
curl http://127.0.0.1:4173/api/profile
```

## 5. 配置 Nginx

```bash
sudo cp /opt/yinlingzhban/deploy/nginx-yinlingzhban.conf /etc/nginx/sites-available/yinlingzhban
sudo ln -sf /etc/nginx/sites-available/yinlingzhban /etc/nginx/sites-enabled/yinlingzhban
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

此时可以用服务器公网 IP 访问网站。绑定域名后，将 Nginx 配置里的 `server_name _;` 改成域名，再补充 HTTPS 证书。

## 6. 阿里云安全组

入方向建议：

- TCP 80：公网访问网站
- TCP 443：HTTPS 访问网站
- TCP 22：只允许自己的固定公网 IP 或使用 Workbench

不需要对公网开放 4173。阿里云安全组官方建议网站开放 80/443，并限制 SSH 来源。

## 7. 发布后的验收

依次确认：

1. 公网 IP 可以打开首页。
2. “查看演示数据”可以加载王阿姨案例。
3. `Qwen live: True` 或问答返回千问实时回答。
4. 新增健康记录后刷新仍然存在。
5. 删除待办后刷新仍保持删除状态。
6. 上传药盒照片后需要点击“确认保存”才进入档案。

当前 JSON 档案适合省赛演示和少量访问。若以后多人同时使用，应把健康档案迁移到数据库或带持久化磁盘的存储中。
