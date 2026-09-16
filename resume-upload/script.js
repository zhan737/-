const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filename = document.getElementById("filename");
const dropError = document.getElementById("dropError");
const finishBtn = document.getElementById("finishBtn");
const uploadAnother = document.getElementById("uploadAnother");
const uploadView = document.getElementById("uploadView");
const successView = document.getElementById("successView");

// 点击上传区 → 打开文件选择框
dropzone.addEventListener("click", () => fileInput.click());

// 键盘可访问性（role=button）
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

// 选中文件后显示文件名
fileInput.addEventListener("change", () => {
  showFile(fileInput.files[0]);
});

// 拖拽上传
["dragenter", "dragover"].forEach((type) =>
  dropzone.addEventListener(type, (e) => {
    e.preventDefault();
    dropzone.classList.add("is-dragover");
  })
);

["dragleave", "drop"].forEach((type) =>
  dropzone.addEventListener(type, (e) => {
    e.preventDefault();
    dropzone.classList.remove("is-dragover");
  })
);

dropzone.addEventListener("drop", (e) => {
  showFile(e.dataTransfer.files[0]);
});

// Finish：已选文件 → 切换到成功视图；未选 → 上传区标红提示
finishBtn.addEventListener("click", () => {
  if (!fileInput.files[0]) {
    dropzone.classList.add("is-error");
    dropError.hidden = false;
    return;
  }
  uploadView.hidden = true;
  successView.hidden = false;
});

// 成功页返回：重置状态，可重新上传
uploadAnother.addEventListener("click", () => {
  fileInput.value = "";
  filename.hidden = true;
  successView.hidden = true;
  uploadView.hidden = false;
});

function showFile(file) {
  if (!file) return;
  dropzone.classList.remove("is-error");
  dropError.hidden = true;
  filename.textContent = `已选择：${file.name}`;
  filename.hidden = false;
}
