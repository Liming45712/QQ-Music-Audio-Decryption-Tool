const TARGET_DLL = "QQMusicCommon.dll";

// 检查 DLL 是否已加载
var targetModule = Process.findModuleByName(TARGET_DLL);
if (!targetModule) {
  console.error("[ERROR] 未找到 " + TARGET_DLL + "，请确保 QQ 音乐已启动");
  throw new Error("未找到目标 DLL: " + TARGET_DLL);
}

console.log("[INFO] 找到 " + TARGET_DLL + " 模块");
console.log("[DEBUG] 模块基址: " + targetModule.base);

// 解析函数地址 - 尝试使用模块对象的 getExportByName 方法
var EncAndDesMediaFileConstructorAddr = null;
var EncAndDesMediaFileDestructorAddr = null;
var EncAndDesMediaFileOpenAddr = null;
var EncAndDesMediaFileGetSizeAddr = null;
var EncAndDesMediaFileReadAddr = null;

try {
  // Frida 16 使用 Module.findExportByName
  console.log("[DEBUG] 使用 Module.findExportByName 查找导出函数");
  EncAndDesMediaFileConstructorAddr = Module.findExportByName(TARGET_DLL, "??0EncAndDesMediaFile@@QAE@XZ");
  EncAndDesMediaFileDestructorAddr = Module.findExportByName(TARGET_DLL, "??1EncAndDesMediaFile@@QAE@XZ");
  EncAndDesMediaFileOpenAddr = Module.findExportByName(TARGET_DLL, "?Open@EncAndDesMediaFile@@QAE_NPB_W_N1@Z");
  EncAndDesMediaFileGetSizeAddr = Module.findExportByName(TARGET_DLL, "?GetSize@EncAndDesMediaFile@@QAEKXZ");
  EncAndDesMediaFileReadAddr = Module.findExportByName(TARGET_DLL, "?Read@EncAndDesMediaFile@@QAEKPAEK_J@Z");
  
  console.log("[DEBUG] 构造函数地址: " + EncAndDesMediaFileConstructorAddr);
  console.log("[DEBUG] 析构函数地址: " + EncAndDesMediaFileDestructorAddr);
  console.log("[DEBUG] Open 函数地址: " + EncAndDesMediaFileOpenAddr);
  console.log("[DEBUG] GetSize 函数地址: " + EncAndDesMediaFileGetSizeAddr);
  console.log("[DEBUG] Read 函数地址: " + EncAndDesMediaFileReadAddr);
} catch (e) {
  console.error("[ERROR] 查找导出函数时出错: " + e);
  console.error("[ERROR] 错误堆栈: " + e.stack);
  throw e;
}

// 检查所有函数地址是否找到
if (!EncAndDesMediaFileConstructorAddr) {
  throw new Error("未找到构造函数地址: ??0EncAndDesMediaFile@@QAE@XZ");
}
if (!EncAndDesMediaFileDestructorAddr) {
  throw new Error("未找到析构函数地址: ??1EncAndDesMediaFile@@QAE@XZ");
}
if (!EncAndDesMediaFileOpenAddr) {
  throw new Error("未找到 Open 函数地址");
}
if (!EncAndDesMediaFileGetSizeAddr) {
  throw new Error("未找到 GetSize 函数地址");
}
if (!EncAndDesMediaFileReadAddr) {
  throw new Error("未找到 Read 函数地址");
}

console.log("[INFO] 所有函数地址已找到");

// 构造函数
var EncAndDesMediaFileConstructor = new NativeFunction(
  EncAndDesMediaFileConstructorAddr, "pointer", ["pointer"], "thiscall"
);
var EncAndDesMediaFileDestructor = new NativeFunction(
  EncAndDesMediaFileDestructorAddr, "void", ["pointer"], "thiscall"
);
var EncAndDesMediaFileOpen = new NativeFunction(
  EncAndDesMediaFileOpenAddr, "bool", ["pointer", "pointer", "bool", "bool"], "thiscall"
);
var EncAndDesMediaFileGetSize = new NativeFunction(
  EncAndDesMediaFileGetSizeAddr, "uint32", ["pointer"], "thiscall"
);
var EncAndDesMediaFileRead = new NativeFunction(
  EncAndDesMediaFileReadAddr, "uint", ["pointer", "pointer", "uint32", "uint64"], "thiscall"
);

console.log("[INFO] 所有 NativeFunction 已创建");

// Windows API: CreateDirectoryW
// Frida 16 使用 Module.findExportByName
var CreateDirectoryW = new NativeFunction(
  Module.findExportByName("kernel32.dll", "CreateDirectoryW"),
  "bool", ["pointer", "pointer"]
);

// 递归创建路径
function ensureDirRecursively(pathStr) {
  const parts = pathStr.split(/[\\/]/);
  let current = parts[0] === "" ? parts[0] + "\\" : parts[0];
  for (let i = 1; i < parts.length; i++) {
    current += "\\" + parts[i];
    const wide = Memory.allocUtf16String(current);
    CreateDirectoryW(wide, ptr(0));
  }
}

console.log("[INFO] 准备导出 decrypt 函数");

rpc.exports = {
  decrypt: function (srcFileName, tmpFileName) {
    console.log("[DEBUG] 开始解密: " + srcFileName);
    // 构造对象
    var EncAndDesMediaFileObject = Memory.alloc(0x28);
    EncAndDesMediaFileConstructor(EncAndDesMediaFileObject);

    var fileNameUtf16 = Memory.allocUtf16String(srcFileName);
    var opened = EncAndDesMediaFileOpen(EncAndDesMediaFileObject, fileNameUtf16, 1, 0);
    if (!opened) {
      EncAndDesMediaFileDestructor(EncAndDesMediaFileObject);
      throw new Error("打开失败: " + srcFileName);
    }

    // 读取数据
    var fileSize = EncAndDesMediaFileGetSize(EncAndDesMediaFileObject);
    var buffer = Memory.alloc(fileSize);
    EncAndDesMediaFileRead(EncAndDesMediaFileObject, buffer, fileSize, 0);

    var data = buffer.readByteArray(fileSize);
    EncAndDesMediaFileDestructor(EncAndDesMediaFileObject);

    // 创建输出目录（递归）
    var lastSlash = tmpFileName.lastIndexOf("\\");
    if (lastSlash !== -1) {
      var dirPath = tmpFileName.substring(0, lastSlash);
      ensureDirRecursively(dirPath);
    }

    // 写入文件
    var tmpFile = new File(tmpFileName, "wb");
    tmpFile.write(data);
    tmpFile.flush();
    tmpFile.close();
    console.log("[DEBUG] 解密完成: " + tmpFileName);
  }
};

console.log("[INFO] decrypt 函数已导出");
