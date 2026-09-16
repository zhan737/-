# crawler-mit-blogs（爬虫笔试题）

分别使用 **Playwright** 和 **DrissionPage** 爬取 https://mitadmissions.org/blogs/ ，结果保存为 CSV。

输出列：`Title | Author | Comment Count | Time | Article Content | Images In Article`

| 文件 | 框架 | 产出 |
|---|---|---|
| `crawl_playwright.py` | Playwright（自带 Chromium，失败时自动回退本机 Chrome/Edge） | `mit_blogs_playwright.csv` |
| `crawl_drissionpage.py` | DrissionPage（驱动本机 Chrome/Edge） | `mit_blogs_drissionpage.csv` |

两个脚本各 16 行结果、内容一致，已实际运行验证（结果 CSV 已包含在仓库中）。

## 安装

```bash
pip install -r requirements.txt          # playwright + DrissionPage
python -m playwright install chromium    # Playwright 首次需下载浏览器
# 国内网络慢可加镜像：
# set PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
```

## 运行

```bash
python crawl_playwright.py               # 输出 mit_blogs_playwright.csv
python crawl_drissionpage.py             # 输出 mit_blogs_drissionpage.csv

# 可选参数
python crawl_playwright.py --pages 2 --max 10 --out result.csv
```

## 实现要点

- **评论数必须用真实浏览器**：列表页评论数由 Disqus `count.js` 在前端渲染
  （静态 HTML 中 `a[href$="#disqus_thread"]` 是空标签），因此爬虫等待其渲染后读取。
- **字段分工**：标题/作者/时间/评论数取自列表页文章卡片（`article.tease`），
  正文取文章页 `.article__body` 的 `innerText`，图片取 `.article__content img`
  并排除作者头像（`page-topper__mug`），多张图以 `; ` 拼接存入单元格。
- **效率**：列表页一次拿到全部卡片和评论数，文章页只请求一次；
  `page.get()` 限制等待时长（Disqus 不可达时会拖住 load 事件，DOM 实际几秒内就绪）。
- **CSV**：`utf-8-sig` 编码，Excel 直接打开不乱码；正文含换行由 csv 模块自动转义。

## 已知环境问题：评论数为空

**评论数由 Disqus 提供，Disqus 在中国大陆网络不可达。** 在有代理的环境下运行即可拿到评论数：

```bash
python crawl_playwright.py --proxy http://127.0.0.1:7890
python crawl_drissionpage.py --proxy http://127.0.0.1:7890
```

无代理时评论数列留空并打印警告（其余字段不受影响）。随仓库提交的 CSV 生成于无代理网络，
故该列为空；在可访问 Disqus 的网络中重跑即会填充。

## 提交到 GitHub

```bash
git init
git add .
git commit -m "feat: crawl mit admissions blogs with playwright and drissionpage"
git remote add origin https://github.com/<你的用户名>/crawler-mit-blogs.git
git push -u origin main
```
