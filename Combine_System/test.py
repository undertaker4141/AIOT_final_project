import cv2
import sys

def test_camera(index=0):
    print(f"正在嘗試開啟相機索引: {index}...")
    cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f"錯誤: 無法開啟編號為 {index} 的相機。")
        return False

    # 設定解析度（有助於某些相機初始化）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    ret, frame = cap.read()

    if ret:
        filename = f"test_cam_{index}.jpg"
        cv2.imwrite(filename, frame)
        print(f"成功！已抓取影像並存為 {filename}")
    else:
        print("錯誤: 雖然相機已開啟，但無法讀取影像幀 (Frame)。")

    cap.release()
    return ret

if __name__ == "__main__":
    # 測試索引 0, 1, 2 (樹莓派有時會跳號)
    for i in range(3):
        if test_camera(i):
            print(f"相機 {i} 測試通過！")
            break
        print("-" * 30)