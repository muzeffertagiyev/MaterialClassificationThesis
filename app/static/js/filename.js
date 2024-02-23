function handleFileSelect() {
  const message = document.getElementById("upload-message");
  const fullPath = document.getElementById("image").value;
  let fileName = fullPath.split('\\').pop().split('/').pop();
  const maxFileNameLength = 115; // Set your desired maximum length

  if (fileName.length > maxFileNameLength) {
      fileName = fileName.slice(0, maxFileNameLength) + "...";
  }

  message.innerHTML = "Selected File: " + fileName;
}