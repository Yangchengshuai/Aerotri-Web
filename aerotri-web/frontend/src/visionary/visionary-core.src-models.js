import * as s from "three/webgpu";
class n {
  object3D;
  mixer;
  clips;
  transform;
  currentAction = null;
  isPlaying = !1;
  isPaused = !1;
  animationSpeed = 1;
  timeScale = 1;
  timeOffset = 0;
  timeUpdateMode = "variable_delta";
  lastUpdateTime = 0;
  frameTime = 0;
  constructor(t, i, e = {}) {
    this.object3D = t, this.clips = i, this.mixer = new s.AnimationMixer(t), this.transform = new Float32Array([
      1,
      0,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      1
    ]), this.applyTransform(), i.length > 0 && (this.currentAction = this.mixer.clipAction(i[0]), this.currentAction.setLoop(s.LoopRepeat, e.loop ? 1 / 0 : 1), e.autoPlay !== !1 && this.startAnimation(e.defaultSpeed || 1));
  }
  /**
   * 应用变换矩阵到 Three.js 对象
   */
  applyTransform() {
    const t = new s.Matrix4();
    t.fromArray(this.transform), this.object3D.matrix.copy(t), this.object3D.matrixAutoUpdate = !1;
  }
  /**
   * 设置变换矩阵
   */
  setTransform(t) {
    this.transform = new Float32Array(t), this.applyTransform();
  }
  /**
   * 获取顶点数量（估算）
   */
  getVertexCount() {
    let t = 0;
    return this.object3D.traverse((i) => {
      if (i instanceof s.Mesh) {
        const e = i.geometry;
        e.attributes.position && (t += e.attributes.position.count);
      }
    }), t;
  }
  /**
   * 设置可见性
   */
  setVisible(t) {
    this.object3D.visible = t;
  }
  /**
   * 获取可见性
   */
  getVisible() {
    return this.object3D.visible;
  }
  // ITimelineTarget 接口实现
  /**
   * 设置动画时间
   */
  setAnimationTime(t) {
    this.currentAction && (this.currentAction.time = t, this.mixer.update(0)), this.frameTime = t;
  }
  /**
   * 设置动画速度
   */
  setAnimationSpeed(t) {
    this.animationSpeed = t, this.currentAction && (this.currentAction.timeScale = t * this.timeScale);
  }
  /**
   * 获取动画速度
   */
  getAnimationSpeed() {
    return this.animationSpeed;
  }
  /**
   * 开始动画
   */
  startAnimation(t) {
    t !== void 0 && this.setAnimationSpeed(t), this.currentAction && (this.currentAction.reset(), this.currentAction.play(), this.isPlaying = !0, this.isPaused = !1);
  }
  /**
   * 暂停动画
   */
  pauseAnimation() {
    this.currentAction && (this.currentAction.paused = !0, this.isPaused = !0);
  }
  /**
   * 恢复动画
   */
  resumeAnimation() {
    this.currentAction && (this.currentAction.paused = !1, this.isPaused = !1);
  }
  /**
   * 停止动画
   */
  stopAnimation() {
    this.currentAction && (this.currentAction.stop(), this.isPlaying = !1, this.isPaused = !1);
  }
  /**
   * 设置时间缩放
   */
  setTimeScale(t) {
    this.timeScale = t, this.currentAction && (this.currentAction.timeScale = this.animationSpeed * t);
  }
  /**
   * 获取时间缩放
   */
  getTimeScale() {
    return this.timeScale;
  }
  /**
   * 设置时间偏移
   */
  setTimeOffset(t) {
    this.timeOffset = t;
  }
  /**
   * 获取时间偏移
   */
  getTimeOffset() {
    return this.timeOffset;
  }
  /**
   * 设置时间更新模式
   */
  setTimeUpdateMode(t) {
    this.timeUpdateMode = t;
  }
  /**
   * 获取时间更新模式
   */
  getTimeUpdateMode() {
    return this.timeUpdateMode;
  }
  /**
   * 获取当前时间
   */
  getCurrentTime() {
    return this.currentAction ? this.currentAction.time : 0;
  }
  /**
   * 是否支持动画
   */
  supportsAnimation() {
    return this.clips.length > 0;
  }
  /**
   * 更新动画（每帧调用）
   */
  update(t) {
    if (this.isPlaying && !this.isPaused) {
      const i = t * this.timeScale;
      this.mixer.update(i), this.frameTime += i;
    }
    this.lastUpdateTime = performance.now();
  }
  /**
   * 切换到指定动画剪辑
   */
  switchToClip(t) {
    return t >= 0 && t < this.clips.length ? (this.currentAction && this.currentAction.stop(), this.currentAction = this.mixer.clipAction(this.clips[t]), this.currentAction.setLoop(s.LoopRepeat, 1 / 0), this.currentAction.timeScale = this.animationSpeed * this.timeScale, this.isPlaying && !this.isPaused && this.currentAction.play(), !0) : !1;
  }
  /**
   * 获取动画剪辑信息
   */
  getClipInfo() {
    return this.clips.map((t) => ({
      name: t.name,
      duration: t.duration
    }));
  }
  /**
   * 销毁资源
   */
  dispose() {
    this.currentAction && this.currentAction.stop(), this.mixer.stopAllAction(), this.object3D.clear();
  }
}
export {
  n as F
};
