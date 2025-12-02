import sounddevice as sd
import numpy as np
import time

def test_correct_alsa_device():
    """使用正确的 ALSA 设备名称测试"""
    print("=== 使用正确的 ALSA 设备名称测试 ===")
    
    # 正确的设备是 card 0, device 0
    alsa_device = 'sysdefault'
    
    print(f"测试设备: {alsa_device}")
    
    try:
        # 测试输入设备
        print("1. 测试输入设备...")
        input_info = sd.query_devices(alsa_device, 'input')
        print(f"✅ 输入设备信息: {input_info['name']}")
        print(f"   默认采样率: {input_info['default_samplerate']}")
        print(f"   输入通道: {input_info['max_input_channels']}")
        
        def volume_callback(indata, frames, time, status):
            if status:
                print(f"状态: {status}")
            rms = np.sqrt(np.mean(indata**2))
            percent = min(rms * 200, 100)
            bar = "█" * int(percent / 2) + " " * (50 - int(percent / 2))
            print(f"输入电平: [{bar}] {percent:5.1f}%", end='\r')
        
        # 使用设备支持的采样率
        sample_rate = int(input_info['default_samplerate'])
        
        with sd.InputStream(device=alsa_device,
                          samplerate=sample_rate,
                          channels=1,
                          callback=volume_callback):
            print("对着麦克风说话... (3秒后停止)")
            time.sleep(3)
        print("\n✅ 输入设备测试成功")
        
    except Exception as e:
        print(f"❌ 输入设备测试失败: {e}")
        return None
    
    try:
        # 测试输出设备
        print("\n2. 测试输出设备...")
        output_info = sd.query_devices(alsa_device, 'output')
        print(f"✅ 输出设备信息: {output_info['name']}")
        print(f"   默认采样率: {output_info['default_samplerate']}")
        print(f"   输出通道: {output_info['max_output_channels']}")
        
        # 使用设备支持的采样率
        sample_rate = int(output_info['default_samplerate'])
        duration = 2
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_audio = 0.1 * np.sin(2 * np.pi * 440 * t)
        
        sd.play(test_audio, samplerate=sample_rate, device=alsa_device)
        sd.wait()
        print("✅ 输出设备测试成功")
        
        return alsa_device
        
    except Exception as e:
        print(f"❌ 输出设备测试失败: {e}")
        return None

# 运行测试
working_device = test_correct_alsa_device()

if working_device:
    print(f"\n🎉 设备测试成功! 使用设备: {working_device}")
else:
    print("\n❌ 设备测试失败")