# Resume Upload Page（前端笔试题）

根据 Figma 设计稿还原的「上传简历」页面，使用原生 HTML / CSS / JavaScript 实现，无任何依赖。

## 预览

直接用浏览器打开 `index.html`，或：

```bash
# 任意静态服务器，例如
npx serve .
```

## 实现的功能

- 两栏布局：左侧文案 + 插画，右侧上传卡片
- 上传区：点击打开文件选择框，支持拖拽上传，hover / 拖拽悬停有状态反馈
- 选择文件后显示文件名
- 点击 Finish：未选文件时上传区标红提示；已选文件时切换到「Resume submitted!」成功页，
  可通过 Upload another file 返回并重置状态
- 按钮具备 hover / active 状态
- 步骤条（3 步）
- 响应式：窄屏（≤860px）时左右结构自动变为上下结构
- 语义化标签：`main` / `section` / `h1` / `h2` / `ol`，上传区使用 `role="button"` 支持键盘操作

## 提交到 GitHub

```bash
git init
git add .
git commit -m "feat: implement resume upload page"
git branch -M main
git remote add origin https://github.com/<你的用户名>/resume-upload.git
git push -u origin main
```

然后开启 GitHub Pages：仓库 **Settings → Pages → Source 选 `main` 分支 `/ (root)`**，
提交 `https://<你的用户名>.github.io/resume-upload/` 即可。

## 备注

- `cat.svg` 是手绘的简化占位插画，建议从 Figma 原稿中选中插画导出 SVG/PNG 后替换同名文件。
