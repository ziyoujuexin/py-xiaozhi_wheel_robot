import sounddevice as sd

def list_audio_devices():
    """列出所有音频设备及其索引"""
    print("=== 所有音频设备 ===")
    devices = sd.query_devices()
    
    print("输入设备:")
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            print(f"  [{i}] {dev['name']}")
            print(f"      输入通道: {dev['max_input_channels']}, 默认采样率: {dev['default_samplerate']}")
    
    print("\n输出设备:")
    for i, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            print(f"  [{i}] {dev['name']}")
            print(f"      输出通道: {dev['max_output_channels']}, 默认采样率: {dev['default_samplerate']}")
    
    print("\n所有设备详情:")
    for i, dev in enumerate(devices):
        print(f"[{i}] {dev['name']}")
        print(f"    输入: {dev['max_input_channels']}通道, 输出: {dev['max_output_channels']}通道")
        print(f"    默认采样率: {dev['default_samplerate']} Hz")

# 运行查询
list_audio_devices()