#Requires AutoHotkey v2.0
#SingleInstance Force
; ==================== KILL SWITCH + AUTO UPDATE ====================
killSwitchURL := "https://gist.githubusercontent.com/tranducanh18/19faff47fe5f7193177e7ceee951a5ea/raw/noHandEdit.txt"
updateURL     := "https://gist.githubusercontent.com/tranducanh18/19faff47fe5f7193177e7ceee951a5ea/raw/auto_fill_xin_chao.ahk"
currentVer    := "1.0"
versionURL    := "https://gist.githubusercontent.com/tranducanh18/19faff47fe5f7193177e7ceee951a5ea/raw/version.txt"

; --- Kiểm tra kill switch ---
SetTimer CheckKillSwitch, 1

CheckKillSwitch(*)
{
    global running, killSwitchURL
    try {
        whr := ComObject("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", killSwitchURL "?t=" A_TickCount, false)
        whr.Send()
        if (whr.Status = 200)
        {
            status := Trim(whr.ResponseText)
            if (status = "off")
            {
                running := false
                MsgBox "Script đã bị tạm dừng bởi tác giả. Vui lòng thử lại sau.", "Thông báo", 48
                ExitApp
            }
        }
    } catch {
        ; Không có mạng → bỏ qua
    }
}
; --- Kiểm tra update ---
try {
    whr2 := ComObject("WinHttp.WinHttpRequest.5.1")
    whr2.Open("GET", versionURL, false)
    whr2.Send()
    latestVer := Trim(whr2.ResponseText)
    if (latestVer != currentVer)
    {
        result := MsgBox("Có phiên bản mới " latestVer "! Cập nhật ngay?", "Update", 4)
        if (result = "Yes")
        {
            whr3 := ComObject("WinHttp.WinHttpRequest.5.1")
            whr3.Open("GET", updateURL, false)
            whr3.Send()
            FileDelete A_ScriptFullPath
            FileAppend whr3.ResponseText, A_ScriptFullPath
            Reload
        }
    }
} catch {
    ; Không có mạng → bỏ qua update
}
; ==================== ẢNH ====================
audioTabImg        := "audio_tab.png"
noiDungLonTiengImg := "noi_dung_lon_tieng.png"
xuatVideoImg       := "xuat_video.png"
fileButtonImg      := "file.png"
hoanTatImg         := "hoan_tat.png"
xoaImg             := "xoa.png"

foundX := 0
foundY := 0
running := false

; ==================== GUI ====================
myGui := Gui("+Resize", "CapCut Auto - Prompt Manager")
myGui.SetFont("s10", "Segoe UI")

myGui.Add("Text",, "Nhập các prompt (mỗi dòng = 1 video):")
promptBox := myGui.Add("Edit", "w520 h300 Multi VScroll", "")

myGui.Add("Text", "xm w520", "Thư mục chứa video:")
folderEdit := myGui.Add("Edit", "w410", "D:\python\hotkry")
myGui.Add("Button", "x+5 w100", "Browse").OnEvent("Click", BrowseFolder)

myGui.Add("Text", "xm", "")
myGui.Add("Button", "xm w130 h35", "▶ Bắt đầu (F1)").OnEvent("Click", (*) => StartProcess())
myGui.Add("Button", "x+10 w130 h35", "■ Dừng (F2)").OnEvent("Click", (*) => StopProcess())
statusTxt := myGui.Add("Text", "xm w520", "Trạng thái: Chờ...")
logBox := myGui.Add("Edit", "xm w520 h120 Multi VScroll ReadOnly", "")

myGui.Show()

BrowseFolder(*)
{
    folder := DirSelect("*" folderEdit.Value, 3, "Chọn thư mục chứa video")
    if folder != ""
        folderEdit.Value := folder
}

Log(msg)
{
    global logBox
    logBox.Value := logBox.Value . "[" A_Hour ":" A_Min ":" A_Sec "] " msg "`n"
}

; ==================== HOTKEYS ====================
F1:: StartProcess()
F2:: StopProcess()

StopProcess(*)
{
    global running
    running := false
    statusTxt.Value := "Trạng thái: Đã dừng."
    Log("⛔ Người dùng đã dừng script.")
}

; ==================== QUÁ TRÌNH CHÍNH ====================
StartProcess(*)
{
    global running, foundX, foundY

    if running
    {
        MsgBox "Script đang chạy! Nhấn F2 để dừng trước.", "Thông báo", 48
        return
    }
    running := true
    logBox.Value := ""

    ; --- Lấy danh sách prompt ---
    raw := promptBox.Value
    blocks := StrSplit(raw, "`n`n")
    cleanPrompts := []
    for b in blocks
    {
        b := Trim(b, "`r`n `t")
        if b != ""
            cleanPrompts.Push(b)
    }

    if cleanPrompts.Length = 0
    {
        MsgBox "Vui lòng nhập ít nhất 1 prompt!", "Lỗi", 48
        running := false
        return
    }

    ; --- Lấy danh sách video ---
    folder := Trim(folderEdit.Value)
    if !DirExist(folder)
    {
        MsgBox "Thư mục không tồn tại:`n" folder, "Lỗi", 48
        running := false
        return
    }

    videoFiles := []
    loop files, folder "\*.mp4"
        videoFiles.Push(A_LoopFileName)
    loop files, folder "\*.avi"
        videoFiles.Push(A_LoopFileName)
    loop files, folder "\*.mov"
        videoFiles.Push(A_LoopFileName)

    if videoFiles.Length = 0
    {
        MsgBox "Không tìm thấy file video trong thư mục!", "Lỗi", 48
        running := false
        return
    }

    totalRounds := Min(cleanPrompts.Length, videoFiles.Length)
    Log("Tìm thấy " videoFiles.Length " video, " cleanPrompts.Length " prompt → chạy " totalRounds " vòng.")

    ; ==================== VÒNG LẶP ====================
    Loop totalRounds
    {
        if !running
            break

        i := A_Index
        currentPrompt := cleanPrompts[i]
        currentFile   := videoFiles[i]

        statusTxt.Value := "Vòng " i "/" totalRounds " — " currentFile
        Log("=== Vòng " i ": " currentFile " ===")

        ; --- Vòng 2 trở đi: detect xoa.png → click → Enter ---
        if i > 1
        {
            Log("Tìm xoa.png...")
            if !WaitAndAction(xoaImg, 10000, "xoa.png", "click")
            {
                running := false
                return
            }
            Sleep 300
            Send "{Enter}"
            Sleep 800
            Log("Đã xóa video cũ.")
        }

        ; --- Click file.png để mở hộp thoại ---
        Log("Tìm file.png...")
        if !WaitAndAction(fileButtonImg, 10000, "file.png", "click")
        {
            running := false
            return
        }
        Sleep 1000

        ; --- Gõ đường dẫn file vào ô File name → Enter ---
        fullPath := folder "\" currentFile
        Send "!n"
        Sleep 400
        Send "^a"
        Sleep 150
        SendText fullPath
        Sleep 400
        Send "{Enter}"
        Sleep 1500
        Log("Đã chọn file: " currentFile)

        ; --- Vòng 1: detect audio_tab → click ---
        if i = 1
        {
            Log("Tìm audio_tab.png...")
            if !WaitAndAction(audioTabImg, 8000, "audio_tab.png", "click")
            {
                running := false
                return
            }
            Sleep 500
            Log("Đã click audio_tab.")
        }

        ; --- Vòng 2+: Ctrl+A → Delete xóa text cũ trước ---
		Send "^a"
		Sleep 200
		Send "{Delete}"
		Sleep 150

        ; --- Detect noi_dung_lon_tieng → click ---
        Log("Tìm noi_dung_lon_tieng.png...")
        if !WaitAndAction(noiDungLonTiengImg, 8000, "noi_dung_lon_tieng.png", "none")
        {
            running := false
            return
        }
        Click foundX + 30, foundY + 50
        Sleep 500

        ; --- Xóa text cũ rồi paste prompt ---
        Send "^a"
        Sleep 200
        Send "{Delete}"
        Sleep 150
        SendText currentPrompt
		
        Sleep 400
        Log("Đã nhập prompt: " currentPrompt)

        ; --- Detect xuat_video → click ---
        Log("Tìm xuat_video.png...")
        if (ImageSearch(&foundX, &foundY, 0, 0, A_ScreenWidth, A_ScreenHeight, xuatVideoImg))
        {
            Click foundX + 30, foundY + 15
            Sleep 1000
            Log("Đã click xuất video.")
        }
        else
        {
            Log("Không thấy xuat_video.png, tìm xuat_video_loi.png...")
            if (ImageSearch(&foundX, &foundY, 0, 0, A_ScreenWidth, A_ScreenHeight, "xuat_video_loi.png"))
            {
                Click foundX + 30, foundY + 15
                Sleep 1000
                Log("Đã click xuat_video_loi.")
            }
            else
            {
                Log("❌ Không tìm thấy cả xuat_video lẫn xuat_video_loi!")
                TrayTip "❌ Không tìm thấy nút xuất video!",, 2
                running := false
                return
            }
        }
        Log("Đang chờ hoàn tất...")

        ; --- Chờ hoan_tat.png (tối đa 10 phút) ---
        statusTxt.Value := "Vòng " i " — Đang xuất video, chờ hoàn tất..."
        if !WaitForImage(hoanTatImg, 600000)
        {
            Log("⚠️ Timeout! Không thấy hoan_tat.png ở vòng " i)
            running := false
            return
        }
        Sleep 500
        Log("Phát hiện Hoàn tất! Nhấn Enter.")

        ; --- Nhấn Enter sau khi hoàn tất ---
        Send "{Enter}"
        Sleep 800
    }

    if running
    {
        statusTxt.Value := "✅ Hoàn thành tất cả " totalRounds " video!"
        Log("✅ Xong! Đã xử lý " totalRounds " video.")
        TrayTip "Hoàn thành tất cả video!",, 3
    }
    running := false
}

; ==================== HÀM TIỆN ÍCH ====================

WaitAndAction(imgFile, waitMs := 5000, label := "", action := "click")
{
    global foundX, foundY
    deadline := A_TickCount + waitMs
    Loop
    {
        if ImageSearch(&foundX, &foundY, 0, 0, A_ScreenWidth, A_ScreenHeight, imgFile)
        {
            if action = "click"
                Click foundX + 30, foundY + 15
            return true
        }
        if A_TickCount > deadline
        {
            TrayTip "❌ Không tìm thấy: " (label != "" ? label : imgFile),, 2
            Log("❌ Không tìm thấy: " (label != "" ? label : imgFile))
            return false
        }
        Sleep 300
    }
}

WaitForImage(imgFile, waitMs := 60000)
{
    global foundX, foundY
    deadline := A_TickCount + waitMs
    Loop
    {
        if ImageSearch(&foundX, &foundY, 0, 0, A_ScreenWidth, A_ScreenHeight, imgFile)
            return true
        if A_TickCount > deadline
            return false
        Sleep 500
    }
}