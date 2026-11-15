#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>
#include <stdio.h>
#include <stdlib.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR args, int show) {
    wchar_t root[32768], python[32768], script[32768], data[32768], logpath[32768], view[32768];
    GetModuleFileNameW(NULL, root, 32768);
    wchar_t *slash = wcsrchr(root, L'\\'); if (!slash) return 1; *slash = 0;
    swprintf(python, 32768, L"%ls\\_runtime\\pythonw.exe", root);
    swprintf(script, 32768, L"%ls\\_app\\main.py", root);
    swprintf(data, 32768, L"%ls\\data", root);
    swprintf(view, 32768, L"%ls\\_desktop", root);
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES || GetFileAttributesW(script) == INVALID_FILE_ATTRIBUTES) {
        MessageBoxW(NULL, L"请先解压整个 LiveWatch 文件夹，再运行 LiveWatch.exe。不要只复制 EXE。", L"LiveWatch", MB_OK|MB_ICONERROR); return 2;
    }
    CreateDirectoryW(data, NULL);
    if (!GetEnvironmentVariableW(L"LIVEWATCH_HOME", NULL, 0)) SetEnvironmentVariableW(L"LIVEWATCH_HOME", data);
    SetEnvironmentVariableW(L"LIVEWATCH_ROOT", root);
    SetEnvironmentVariableW(L"LIVEWATCH_PORTABLE", L"1");
    SetEnvironmentVariableW(L"FLET_VIEW_PATH", view);
    swprintf(logpath, 32768, L"%ls\\startup.log", data);
    SECURITY_ATTRIBUTES security = {sizeof(SECURITY_ATTRIBUTES), NULL, TRUE};
    HANDLE log = CreateFileW(logpath, FILE_APPEND_DATA, FILE_SHARE_READ|FILE_SHARE_WRITE, &security, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    HANDLE input = CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ|FILE_SHARE_WRITE, &security, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (log == INVALID_HANDLE_VALUE) { MessageBoxW(NULL,L"当前目录不可写。请把整个文件夹解压到桌面或其他可写位置。",L"LiveWatch",MB_OK|MB_ICONERROR); return 3; }
    size_t size = wcslen(python)+wcslen(script)+wcslen(args)+16;
    wchar_t *command = calloc(size,sizeof(wchar_t));
    if (!command) return 4;
    swprintf(command,size,L"\"%ls\" \"%ls\" %ls",python,script,args);
    STARTUPINFOW si = {0}; si.cb=sizeof(si); si.dwFlags=STARTF_USESTDHANDLES; si.hStdInput=input; si.hStdOutput=log; si.hStdError=log;
    PROCESS_INFORMATION pi = {0};
    BOOL ok=CreateProcessW(python,command,NULL,NULL,TRUE,CREATE_NO_WINDOW,NULL,root,&si,&pi);
    free(command); CloseHandle(log); CloseHandle(input);
    if (!ok) { MessageBoxW(NULL,L"Windows 无法启动内置运行时，请检查压缩包是否完整。",L"LiveWatch",MB_OK|MB_ICONERROR); return 5; }
    WaitForSingleObject(pi.hProcess,INFINITE); DWORD code=0; GetExitCodeProcess(pi.hProcess,&code); CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    if (code) MessageBoxW(NULL,L"程序启动或运行异常，详情保存在 data\\startup.log。",L"LiveWatch",MB_OK|MB_ICONERROR);
    return (int)code;
}
