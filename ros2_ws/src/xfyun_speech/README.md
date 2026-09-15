# 讯飞 WebAPI 语音链路

该包通过讯飞官方 WebSocket API 提供流式语音听写和语音合成，不依赖 AIUI
专有动态库。`deepseek_ros2` 负责文字问答，两者由
`voice_assistant.launch.py` 连接。

## 凭据

在讯飞同一个 WebAPI 应用中开通“语音听写（流式版）”和“在线语音合成”。
启动前从本机私有文件导出变量，不要写入仓库、ROS 参数或启动文件：

```bash
export XFYUN_APP_ID='...'
export XFYUN_API_KEY='...'
export XFYUN_API_SECRET='...'
export DEEPSEEK_API_KEY='...'
```

Orin 上还需要 `alsa-utils` 与 Python `websocket-client`。Ubuntu 22.04 可安装
`alsa-utils python3-websocket`。

## 构建与启动

```bash
cd /home/wheeltec/ROSCAR/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select deepseek_ros2 voice_command_router xfyun_speech --symlink-install
source install/setup.bash
ros2 launch xfyun_speech voice_assistant.launch.py enable_tts:=true enable_buzzer:=false
```

板子启动脚本会额外启动厂商 `wheeltec_mic` 串口节点，但仅使用其硬件唤醒事件，
不会启动厂商离线识别、反馈音频或运动控制。默认唤醒词是“小微小微”：说出
唤醒词、停顿约 1 秒后再说问题，可信的 `/voice_words=小车唤醒` 会触发一轮录音。没有唤醒驱动时
也可以手动触发：

```bash
ros2 service call /voice/start_listening std_srvs/srv/Trigger '{}'
```

分层测试：

```bash
# 只测 DeepSeek → TTS
ros2 topic pub --once /voice/asr_text std_msgs/msg/String "{data: '介绍一下你自己'}"

# 只测讯飞 TTS 与声卡
ros2 topic pub --once /voice/tts_text std_msgs/msg/String "{data: '语音合成测试'}"
```

Orin 实测阵列录音使用 `plughw:CARD=XFMDPV0018,DEV=0`，支持
16 kHz、16-bit、单声道采集。播放使用同一阵列中的 C-Media USB 音频设备
`plughw:CARD=Device,DEV=0`；厂商反馈音频代码也使用此设备。两者虽然在同一
麦克风组件中，Linux 下是两个不同声卡。已写入板子默认配置，启动脚本默认启用
TTS；首次测试合成音量设置为 30。换设备后分别用 `arecord -l`、`aplay -l`
确认声卡并调整参数。若暂时不需要播放，给启动脚本追加 `enable_tts:=false`。
当前链路不发布 `cmd_vel`，也不启动底盘控制节点。

TTS 节点把 `/voice/tts_text` 转成 16 kHz 单声道 PCM，直接通过 ALSA 播放。
开始播放时发布 `/voice/speaking=true`，ASR 在播报期间不接收唤醒，避免阵列
听到自己的回复后再次提问。`/voice/tts_state` 会发布 `SPEAKING`、`IDLE`
或错误信息。讯飞应用还需开通“在线语音合成”；如果 API 返回权限/发音人错误，
应在讯飞控制台核对当前应用及 `xiaoyan` 发音人权限。首次测试用户已听到短
测试语音及 DeepSeek 自我介绍；更换设备后仍应重新确认阵列喇叭和实际音量。

DeepSeek 最终回答同时发布到 `/voice/assistant_text`，并按 JSON Lines 追加保存到
`/home/wheeltec/ROSCAR/logs/deepseek_responses.jsonl`。可持续查看：

```bash
tail -f /home/wheeltec/ROSCAR/logs/deepseek_responses.jsonl
```

`buzz(duration_ms)` 工具和 `voice_command_router` 的白名单校验代码仍保留，
但当前 `enable_tools=false`，不会向 DeepSeek 开放蜂鸣能力，也不会声称已鸣响。
工具调用若日后启用，仍必须经路由节点二次校验，100--2000 ms 以外会被拒绝。
蜂鸣器属于下位机，GPIO 适配器仅为可选占位，后续须根据底盘协议写适配器，
不能猜测 Jetson GPIO。
