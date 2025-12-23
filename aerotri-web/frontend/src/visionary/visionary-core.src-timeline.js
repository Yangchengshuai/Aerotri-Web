var i = /* @__PURE__ */ ((a) => (a.STOPPED = "stopped", a.PLAYING = "playing", a.PAUSED = "paused", a))(i || {});
class h {
  _playbackState = i.STOPPED;
  _animationSpeed = 1;
  _eventListeners = [];
  /**
   * 获取当前播放状态
   */
  get playbackState() {
    return this._playbackState;
  }
  /**
   * 获取动画速度
   */
  get animationSpeed() {
    return this._animationSpeed;
  }
  /**
   * 是否正在播放
   */
  get isPlaying() {
    return this._playbackState === i.PLAYING;
  }
  /**
   * 是否暂停
   */
  get isPaused() {
    return this._playbackState === i.PAUSED;
  }
  /**
   * 是否停止
   */
  get isStopped() {
    return this._playbackState === i.STOPPED;
  }
  /**
   * 开始播放动画
   * @param speed 动画速度倍数
   */
  play(e = 1) {
    this._animationSpeed = Math.max(0.1, e), this._playbackState = i.PLAYING, this._emitEvent({
      type: "play",
      timestamp: performance.now(),
      data: { speed: this._animationSpeed }
    }), console.log(`🎬 Animation started at ${this._animationSpeed}x speed`);
  }
  /**
   * 暂停动画
   */
  pause() {
    this._playbackState === i.PLAYING ? (this._playbackState = i.PAUSED, this._emitEvent({
      type: "pause",
      timestamp: performance.now()
    }), console.log("⏸️ Animation paused")) : console.warn("Cannot pause: animation is not playing");
  }
  /**
   * 恢复动画
   */
  resume() {
    this._playbackState === i.PAUSED ? (this._playbackState = i.PLAYING, this._emitEvent({
      type: "resume",
      timestamp: performance.now()
    }), console.log("▶️ Animation resumed")) : console.warn("Cannot resume: animation is not paused");
  }
  /**
   * 停止动画
   */
  stop() {
    this._playbackState = i.STOPPED, this._emitEvent({
      type: "stop",
      timestamp: performance.now()
    }), console.log("⏹️ Animation stopped");
  }
  /**
   * 设置动画速度
   * @param speed 动画速度倍数
   */
  setSpeed(e) {
    const t = this._animationSpeed;
    this._animationSpeed = Math.max(0.1, e), t !== this._animationSpeed && (this._emitEvent({
      type: "speedChange",
      timestamp: performance.now(),
      data: {
        oldSpeed: t,
        newSpeed: this._animationSpeed
      }
    }), console.log(`🎯 Animation speed changed from ${t}x to ${this._animationSpeed}x`));
  }
  /**
   * 获取动画速度
   * @returns 当前动画速度
   */
  getSpeed() {
    return this._animationSpeed;
  }
  /**
   * 重置状态到停止
   */
  reset() {
    this._playbackState = i.STOPPED, this._animationSpeed = 1, this._emitEvent({
      type: "stop",
      timestamp: performance.now(),
      data: { reset: !0 }
    }), console.log("🔄 Animation state reset");
  }
  /**
   * 添加事件监听器
   * @param listener 事件监听器
   */
  addEventListener(e) {
    this._eventListeners.push(e);
  }
  /**
   * 移除事件监听器
   * @param listener 事件监听器
   */
  removeEventListener(e) {
    const t = this._eventListeners.indexOf(e);
    t > -1 && this._eventListeners.splice(t, 1);
  }
  /**
   * 清除所有事件监听器
   */
  clearEventListeners() {
    this._eventListeners = [];
  }
  /**
   * 获取状态信息
   * @returns 状态信息对象
   */
  getStateInfo() {
    return {
      playbackState: this._playbackState,
      animationSpeed: this._animationSpeed,
      isPlaying: this.isPlaying,
      isPaused: this.isPaused,
      isStopped: this.isStopped
    };
  }
  /**
   * 发出事件
   * @param event 事件对象
   */
  _emitEvent(e) {
    this._eventListeners.forEach((t) => {
      try {
        t(e);
      } catch (s) {
        console.error("Error in animation state event listener:", s);
      }
    });
  }
}
var p = /* @__PURE__ */ ((a) => (a.FIXED_DELTA = "fixed_delta", a.VARIABLE_DELTA = "variable_delta", a))(p || {});
class l {
  /**
   * 根据更新模式计算时间增量
   * @param params 时间计算参数
   * @returns 时间增量 (秒)
   */
  static calculateDeltaTime(e) {
    const { mode: t, currentTime: s, lastUpdateTime: n, fixedDeltaTime: m, maxDeltaTime: o } = e;
    switch (t) {
      case "fixed_delta":
        return m;
      case "variable_delta":
        if (n === 0)
          return 0;
        let r = (s - n) / 1e3;
        return r = Math.min(Math.max(r, 0), o), r;
      default:
        return console.warn(`Unknown time update mode: ${t}, using fixed delta`), m;
    }
  }
  /**
   * 检查时间更新模式是否有效
   * @param mode 时间更新模式
   * @returns 是否有效
   */
  static isValidMode(e) {
    return Object.values(p).includes(e);
  }
  /**
   * 从字符串转换为 TimeUpdateMode 枚举
   * @param modeString 模式字符串
   * @returns TimeUpdateMode 枚举值
   */
  static fromString(e) {
    return this.isValidMode(e) ? e : (console.warn(`Invalid time update mode: ${e}, defaulting to FIXED_DELTA`), "fixed_delta");
  }
  /**
   * 获取默认的固定时间步长
   * @returns 默认固定时间步长 (秒)
   */
  static getDefaultFixedDeltaTime() {
    return 0.016 * 1.1;
  }
  /**
   * 获取默认的最大时间步长
   * @returns 默认最大时间步长 (秒)
   */
  static getDefaultMaxDeltaTime() {
    return 0.05;
  }
  /**
   * 获取时间更新模式的描述
   * @param mode 时间更新模式
   * @returns 模式描述
   */
  static getModeDescription(e) {
    switch (e) {
      case "fixed_delta":
        return "固定时间步长 - 每帧使用固定的时间增量，确保动画播放稳定";
      case "variable_delta":
        return "可变时间步长 - 根据实际帧间隔计算时间增量，更接近真实时间";
      default:
        return "未知模式";
    }
  }
}
class d {
  _frameTime = -1;
  _lastUpdateTime = 0;
  _config;
  constructor(e = {}) {
    this._config = {
      timeScale: 1,
      timeOffset: 0,
      timeUpdateMode: "fixed_delta",
      animationSpeed: 1,
      fixedDeltaTime: l.getDefaultFixedDeltaTime(),
      maxDeltaTime: l.getDefaultMaxDeltaTime(),
      ...e
    };
  }
  /**
   * 获取当前帧时间
   */
  get frameTime() {
    return this._frameTime;
  }
  /**
   * 获取配置
   */
  get config() {
    return { ...this._config };
  }
  /**
   * 更新配置
   * @param newConfig 新的配置
   */
  updateConfig(e) {
    this._config = { ...this._config, ...e };
  }
  /**
   * 设置时间缩放
   * @param scale 时间缩放因子
   */
  setTimeScale(e) {
    this._config.timeScale = Math.max(0.01, e), console.log(`[TimeCalculator] Time scale set to: ${this._config.timeScale}`);
  }
  /**
   * 获取时间缩放
   * @returns 当前时间缩放因子
   */
  getTimeScale() {
    return this._config.timeScale;
  }
  /**
   * 设置时间偏移
   * @param offset 时间偏移量 (秒)
   */
  setTimeOffset(e) {
    this._config.timeOffset = e, console.log(`[TimeCalculator] Time offset set to: ${this._config.timeOffset}`);
  }
  /**
   * 获取时间偏移
   * @returns 当前时间偏移量
   */
  getTimeOffset() {
    return this._config.timeOffset;
  }
  /**
   * 设置时间更新模式
   * @param mode 时间更新模式
   */
  setTimeUpdateMode(e) {
    this._config.timeUpdateMode = e, e === "variable_delta" && (this._lastUpdateTime = 0), console.log(`[TimeCalculator] Time update mode set to: ${e}`);
  }
  /**
   * 获取时间更新模式
   * @returns 当前时间更新模式
   */
  getTimeUpdateMode() {
    return this._config.timeUpdateMode;
  }
  /**
   * 设置动画速度
   * @param speed 动画速度倍数
   */
  setAnimationSpeed(e) {
    this._config.animationSpeed = Math.max(0.1, e), console.log(`[TimeCalculator] Animation speed set to: ${this._config.animationSpeed}`);
  }
  /**
   * 获取动画速度
   * @returns 当前动画速度
   */
  getAnimationSpeed() {
    return this._config.animationSpeed;
  }
  /**
   * 计算时间增量并更新帧时间
   * @param rafNow 当前时间戳 (performance.now())
   * @param isPlaying 是否正在播放
   * @param isPaused 是否暂停
   * @returns 时间计算结果
   */
  calculateTime(e = performance.now(), t = !0, s = !1) {
    let n = 0, m = !1;
    t && !s ? (this._lastUpdateTime, this._config.timeScale, this._config.animationSpeed, this._config.timeUpdateMode, this._config.fixedDeltaTime, this._config.maxDeltaTime, n = l.calculateDeltaTime({
      mode: this._config.timeUpdateMode,
      currentTime: e,
      lastUpdateTime: this._lastUpdateTime,
      fixedDeltaTime: this._config.fixedDeltaTime,
      maxDeltaTime: this._config.maxDeltaTime
    }), n *= this._config.timeScale * this._config.animationSpeed, this._frameTime += n, m = !0) : s && this._config.timeUpdateMode === "variable_delta" && (this._lastUpdateTime = e), this._lastUpdateTime = e;
    const o = this.getAdjustedTime();
    return {
      deltaTime: n,
      frameTime: this._frameTime,
      adjustedTime: o,
      shouldUpdate: m
    };
  }
  /**
   * 获取调整后的时间 (应用了时间偏移)
   * @returns 调整后的时间
   */
  getAdjustedTime() {
    return (this._frameTime - this._config.timeOffset) * this._config.timeScale;
  }
  /**
   * 设置当前时间
   * @param time 时间值 (秒)
   */
  setTime(e) {
    this._frameTime = e, this._lastUpdateTime = 0, console.log(`[TimeCalculator] Time set to: ${e.toFixed(3)}s`);
  }
  /**
   * 重置时间到零
   */
  resetTime() {
    this._frameTime = 0, this._lastUpdateTime = 0, console.log("[TimeCalculator] Time reset to 0");
  }
  /**
   * 获取性能统计信息
   * @returns 统计信息
   */
  getStats() {
    return {
      frameTime: this._frameTime,
      adjustedTime: this.getAdjustedTime(),
      timeScale: this._config.timeScale,
      timeOffset: this._config.timeOffset,
      timeUpdateMode: this._config.timeUpdateMode,
      animationSpeed: this._config.animationSpeed,
      lastUpdateTime: this._lastUpdateTime
    };
  }
  /**
   * 克隆时间计算器
   * @returns 新的时间计算器实例
   */
  clone() {
    const e = new d(this._config);
    return e._frameTime = this._frameTime, e._lastUpdateTime = this._lastUpdateTime, e;
  }
}
const c = -0.5;
class f {
  animationState;
  timeCalculator;
  config;
  frameCount = 0;
  eventListeners = [];
  constructor(e = {}) {
    this.config = {
      timeScale: 1,
      timeOffset: 0,
      timeUpdateMode: "fixed_delta",
      animationSpeed: 1,
      fixedDeltaTime: 0.016 * 1.1,
      // 约 60 FPS
      maxDeltaTime: 0.05,
      // 50ms
      ...e
    }, this.animationState = new h(), this.timeCalculator = new d(this.config), this.animationState.addEventListener((t) => {
      this._emitEvent(t);
    });
  }
  /**
   * 播放控制方法
   */
  /**
   * 开始播放
   * @param speed 播放速度倍数
   */
  start(e) {
    this.animationState.play(e);
  }
  /**
   * 暂停播放
   */
  pause() {
    this.animationState.pause();
  }
  /**
   * 恢复播放
   */
  resume() {
    this.animationState.resume();
  }
  /**
   * 停止播放
   */
  stop() {
    this.animationState.stop(), this.frameCount = 0;
  }
  /**
   * 时间控制方法
   */
  /**
   * 设置当前时间
   * @param time 时间值 (秒)
   */
  setTime(e) {
    this.timeCalculator.setTime(e), this._emitEvent({
      type: "timeChange",
      timestamp: performance.now(),
      data: { time: e }
    });
  }
  /**
   * 设置播放速度
   * @param speed 播放速度倍数
   */
  setSpeed(e) {
    this.animationState.setSpeed(e), this.timeCalculator.setAnimationSpeed(e);
  }
  /**
   * 设置时间缩放
   * @param scale 时间缩放因子
   */
  setTimeScale(e) {
    this.timeCalculator.setTimeScale(e), this.config.timeScale = e;
  }
  /**
   * 设置时间偏移
   * @param offset 时间偏移量 (秒)
   */
  setTimeOffset(e) {
    this.timeCalculator.setTimeOffset(e), this.config.timeOffset = e;
  }
  /**
   * 设置时间更新模式
   * @param mode 时间更新模式
   */
  setTimeUpdateMode(e) {
    this.timeCalculator.setTimeUpdateMode(e), this.config.timeUpdateMode = e;
  }
  /**
   * 兼容性方法 - 为了保持与现有代码的兼容性
   */
  /**
   * 开始动画 (兼容性方法)
   * @param speed 动画速度
   */
  startAnimation(e = 1) {
    this.start(e);
  }
  /**
   * 暂停动画 (兼容性方法)
   */
  pauseAnimation() {
    this.pause();
  }
  /**
   * 恢复动画 (兼容性方法)
   */
  resumeAnimation() {
    this.resume();
  }
  /**
   * 停止动画 (兼容性方法)
   */
  stopAnimation() {
    this.stop();
  }
  /**
   * 设置动画时间 (兼容性方法)
   * @param time 动画时间
   */
  setAnimationTime(e) {
    this.setTime(e);
  }
  /**
   * 设置动画速度 (兼容性方法)
   * @param speed 动画速度
   */
  setAnimationSpeed(e) {
    this.setSpeed(e);
  }
  /**
   * 获取动画速度 (兼容性方法)
   * @returns 当前动画速度
   */
  getAnimationSpeed() {
    return this.animationState.getSpeed();
  }
  /**
   * 获取时间缩放 (兼容性方法)
   * @returns 当前时间缩放因子
   */
  getTimeScale() {
    return this.timeCalculator.getTimeScale();
  }
  /**
   * 获取时间偏移 (兼容性方法)
   * @returns 当前时间偏移量
   */
  getTimeOffset() {
    return this.timeCalculator.getTimeOffset();
  }
  /**
   * 获取时间更新模式 (兼容性方法)
   * @returns 当前时间更新模式
   */
  getTimeUpdateMode() {
    return this.timeCalculator.getTimeUpdateMode();
  }
  /**
   * 时间计算方法
   */
  /**
   * 更新时间轴 (每帧调用)
   * @param rafNow 当前时间戳
   * @returns 调整后的当前时间
   */
  update(e) {
    const t = this.timeCalculator.calculateTime(
      e,
      this.animationState.isPlaying,
      this.animationState.isPaused
    );
    return t.shouldUpdate && this.frameCount++, t.adjustedTime;
  }
  /**
   * 获取当前时间
   * @returns 当前时间
   */
  getCurrentTime() {
    return this.timeCalculator.getAdjustedTime();
  }
  /**
   * 获取原始帧时间（未调整的时间）
   * @returns 原始帧时间
   */
  getFrameTime() {
    return this.timeCalculator.frameTime;
  }
  /**
   * 检查是否处于 fallback preview 模式
   * @returns 如果 frameTime < FALLBACK_PREVIEW_THRESHOLD，返回 true
   */
  isFallbackPreviewMode() {
    return this.timeCalculator.frameTime < c;
  }
  /**
   * 状态查询方法
   */
  /**
   * 是否正在播放
   * @returns 是否正在播放
   */
  isPlaying() {
    return this.animationState.isPlaying;
  }
  /**
   * 是否暂停
   * @returns 是否暂停
   */
  isPaused() {
    return this.animationState.isPaused;
  }
  /**
   * 是否停止
   * @returns 是否停止
   */
  isStopped() {
    return this.animationState.isStopped;
  }
  /**
   * 是否支持动画
   * @returns 总是返回 true
   */
  supportsAnimation() {
    return !0;
  }
  /**
   * 获取时间轴统计信息
   * @returns 统计信息
   */
  getStats() {
    const e = this.timeCalculator.getStats(), t = this.animationState.getStateInfo();
    return {
      currentTime: e.frameTime,
      adjustedTime: e.adjustedTime,
      timeScale: e.timeScale,
      timeOffset: e.timeOffset,
      timeUpdateMode: e.timeUpdateMode,
      animationSpeed: e.animationSpeed,
      playbackState: t.playbackState,
      isPlaying: t.isPlaying,
      isPaused: t.isPaused,
      isStopped: t.isStopped,
      lastUpdateTime: e.lastUpdateTime,
      frameCount: this.frameCount
    };
  }
  /**
   * 清除所有事件监听器
   */
  clearEventListeners() {
    this.eventListeners = [], this.animationState.clearEventListeners();
  }
  /**
   * 发出事件
   * @param event 事件对象
   */
  _emitEvent(e) {
    this.eventListeners.forEach((t) => {
      try {
        t(e);
      } catch (s) {
        console.error("Error in timeline event listener:", s);
      }
    });
  }
  /**
   * 导出常量供外部使用
   */
  static FALLBACK_PREVIEW_THRESHOLD = c;
}
export {
  f as T,
  p as a
};
