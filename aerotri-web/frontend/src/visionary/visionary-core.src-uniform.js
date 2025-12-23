class s {
  buffer;
  bindGroup;
  label;
  size;
  _data;
  device;
  /**
   * Create bind group layout for uniform buffers
   * Cached per device for efficiency
   */
  static bindGroupLayout(e) {
    return e.createBindGroupLayout({
      label: "uniform bind group layout",
      entries: [{
        binding: 0,
        visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT | GPUShaderStage.COMPUTE,
        buffer: { type: "uniform" }
      }]
    });
  }
  constructor(e, t, r) {
    this.device = e, this.label = r;
    const i = t instanceof ArrayBuffer ? new Uint8Array(t) : new Uint8Array(t.buffer, t.byteOffset, t.byteLength);
    this.size = i.byteLength, this._data = new ArrayBuffer(this.size), new Uint8Array(this._data).set(i), this.buffer = e.createBuffer({
      label: r,
      size: this.size,
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
      mappedAtCreation: !1
    }), e.queue.writeBuffer(this.buffer, 0, this._data), this.bindGroup = e.createBindGroup({
      label: r ? `${r} bind group` : void 0,
      layout: s.bindGroupLayout(e),
      entries: [{ binding: 0, resource: { buffer: this.buffer } }]
    });
  }
  /**
   * Get a copy of the current CPU-side data
   */
  get data() {
    return this._data.slice(0);
  }
  /**
   * Replace CPU-side data (must call flush() to upload)
   */
  set dataBytes(e) {
    if (e.byteLength !== this.size)
      throw new Error(`Uniform size mismatch: expected ${this.size}, got ${e.byteLength}`);
    this._data = e.slice(0);
  }
  /**
   * Update from a typed array view (size must match)
   */
  setData(e) {
    if (e.byteLength !== this.size)
      throw new Error(`Uniform size mismatch: expected ${this.size}, got ${e.byteLength}`);
    new Uint8Array(this._data).set(
      new Uint8Array(e.buffer, e.byteOffset, e.byteLength)
    );
  }
  /**
   * Upload CPU-side data to the GPU
   */
  flush(e) {
    (e || this.device).queue.writeBuffer(this.buffer, 0, new Uint8Array(this._data));
  }
  /**
   * Create a clone with the same data
   */
  clone(e) {
    const t = e || this.device;
    return new s(t, this._data, this.label);
  }
  /**
   * Destroy GPU resources
   */
  destroy() {
    this.buffer.destroy();
  }
}
export {
  s as U
};
