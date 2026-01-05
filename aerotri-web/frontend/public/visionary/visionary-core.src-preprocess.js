import { p as f } from "./visionary-core.src-shaders.js";
import { U as p } from "./visionary-core.src-uniform.js";
import { V as c, e as d } from "./visionary-core.src-utils.js";
class g {
  pipeline;
  pipelineLayout;
  cameraUniforms;
  settingsUniforms;
  shDegree = 3;
  device;
  m_useRawColor = !1;
  // Pre-allocated scratch buffers to avoid per-frame allocations
  scratchCameraBuffer = new ArrayBuffer(272);
  scratchCameraView = new Float32Array(this.scratchCameraBuffer);
  scratchSettingsBuffer = new ArrayBuffer(80);
  scratchSettingsView = new DataView(this.scratchSettingsBuffer);
  /**
   * Initialize GPU resources for preprocessing
   */
  async initialize(r, i, e = !1) {
    this.device = r, this.shDegree = i, this.cameraUniforms = new p(r, new ArrayBuffer(272), "Camera Uniforms"), this.settingsUniforms = new p(r, new ArrayBuffer(80), "Settings Uniforms"), this.pipelineLayout = r.createPipelineLayout({
      label: "preprocess pipeline layout",
      bindGroupLayouts: [
        p.bindGroupLayout(r),
        // @group(0) - Camera
        this.getPointCloudBindGroupLayout(r),
        // @group(1) - PointCloud
        this.getSortBindGroupLayout(r),
        // @group(2) - Sort
        // Merge model params into group(3) as binding(1) to keep BGL count ≤ 4
        // @group(3) will host: binding(0) RenderSettings, binding(1) ModelParams
        this.getSettingsAndModelParamsBGL(r)
        // @group(3)
      ]
    });
    const t = f.replace("<injected>", i.toString()), o = r.createShaderModule({
      label: "preprocess.wgsl",
      code: t
    });
    this.pipeline = r.createComputePipeline({
      label: "preprocess pipeline",
      layout: this.pipelineLayout,
      compute: {
        module: o,
        entryPoint: "preprocess",
        constants: {
          USE_RAW_COLOR: e ? 1 : 0
        }
      }
    }), this.m_useRawColor = e, console.log(`📐 Preprocessor initialized with SH degree ${i}, raw color: ${e}`);
  }
  /**
   * Execute preprocessing compute pass (Phase A 单模型路径，保留兼容)
   */
  // should be throwed
  // preprocess(args: PreprocessArgs, encoder: GPUCommandEncoder): void {
  //   // Pack uniforms
  //   this.packCameraUniforms(args.camera, args.viewport);
  //   this.packSettingsUniforms(args.pointCloud, args.settings);
  //   const initialNumPoints = args.pointCloud.numPoints;
  //   this.packModelParams(this.identityMat4(), 0, initialNumPoints); // 默认单位矩阵 + baseOffset=0 + numPoints
  //   console.log(`📐 Initial num_points packed in CPU buffer: ${initialNumPoints}` + ` using RAWRGB? ${this.m_useRawColor}`);
  //   if (args.countBuffer) {
  //     console.log(`ONNX count buffer detected - will overwrite num_points after flush`);
  //   }
  //   // Flush camera and settings uniforms first
  //   this.cameraUniforms.flush(this.device);
  //   this.settingsUniforms.flush(this.device);
  //   // Handle ONNX count buffer if provided
  //   if (args.countBuffer) {
  //     // IMPORTANT: Flush FIRST to write model matrix and baseOffset
  //     this.modelParamsUniforms.flush(this.device);
  //     // THEN copy ONNX count to overwrite ONLY the num_points field at offset 68
  //     encoder.copyBufferToBuffer(
  //       args.countBuffer,                    // src (ONNX count buffer)
  //       0,                                   // srcOffset
  //       this.modelParamsUniforms.buffer,     // dst (ModelParams buffer)
  //       68,                                  // dstOffset (num_points field at byte 68)
  //       4                                    // size (4 bytes for u32)
  //     );
  //     console.log('Copied ONNX count to ModelParams.num_points at offset 68 (AFTER flush)');
  //     // Store for debugging later
  //     (this as any)._debugCountBuffer = args.countBuffer;
  //     (this as any)._debugMaxPoints = initialNumPoints;
  //   } else {
  //     // Normal path: just flush when no ONNX count buffer
  //     this.modelParamsUniforms.flush(this.device);
  //   }
  //   // Begin compute pass
  //   const computePass = encoder.beginComputePass({ 
  //     label: 'preprocess compute pass' 
  //   });
  //   // Set pipeline and bind groups
  //   computePass.setPipeline(this.pipeline);
  //   computePass.setBindGroup(0, this.cameraUniforms.bindGroup);
  //   computePass.setBindGroup(1, args.pointCloud.bindGroup());
  //   computePass.setBindGroup(2, this.getSortBindGroup(args.sortStuff));
  //   // group(3): settings + model params packed in one bind group layout
  //   const smBGL = this.pipeline.getBindGroupLayout(3);
  //   const smBG = this.device.createBindGroup({
  //     layout: smBGL,
  //     entries: [
  //       { binding: 0, resource: { buffer: this.settingsUniforms.buffer } },
  //       { binding: 1, resource: { buffer: this.modelParamsUniforms.buffer } },
  //     ],
  //   });
  //   computePass.setBindGroup(3, smBG);
  //   // Dispatch workgroups (256 threads per workgroup)
  //   const workgroupSize = 256;
  //   const workgroups = Math.ceil(args.pointCloud.numPoints / workgroupSize);
  //   computePass.dispatchWorkgroups(workgroups, 1, 1);
  //   computePass.end();
  // }
  /**
   * Phase B / M1：多模型全局路径的单模型调度
   * 将当前模型写入全局缓冲的指定区段 [baseOffset, baseOffset + count)
   */
  dispatchModel(r, i) {
    if (this.packCameraUniforms(r.camera, r.viewport), this.packSettingsUniforms(r.pointCloud, r.settings), r.pointCloud.updateModelParamsWithOffset(r.modelMatrix, r.baseOffset), this.cameraUniforms.flush(this.device), this.settingsUniforms.flush(this.device), "setPrecisionForShader" in r.pointCloud && typeof r.pointCloud.setPrecisionForShader == "function")
      try {
        r.pointCloud.setPrecisionForShader();
      } catch {
      }
    r.countBuffer ? (r.pointCloud.modelParamsUniforms.flush(this.device), i.copyBufferToBuffer(
      r.countBuffer,
      // src (ONNX count buffer)
      0,
      // srcOffset
      r.pointCloud.modelParamsUniforms.buffer,
      // dst (ModelParams buffer)
      68,
      // dstOffset (num_points field at byte 68)
      4
      // size (4 bytes for u32)
    )) : r.pointCloud.modelParamsUniforms.flush(this.device);
    const e = i.beginComputePass({ label: "preprocess compute pass (global/M1)" });
    e.setPipeline(this.pipeline), e.setBindGroup(0, this.cameraUniforms.bindGroup);
    const t = this.pipeline.getBindGroupLayout(1), o = r.pointCloud.getSplatBuffer(), n = this.device.createBindGroup({
      label: "preprocess/pc-global-bg",
      layout: t,
      entries: [
        { binding: 0, resource: { buffer: o.gaussianBuffer } },
        { binding: 1, resource: { buffer: o.shBuffer } },
        { binding: 2, resource: { buffer: r.global.splat2D } },
        // 全局输出
        { binding: 3, resource: { buffer: r.pointCloud.uniforms.buffer } }
      ]
    });
    e.setBindGroup(1, n), e.setBindGroup(2, this.getSortBindGroup(r.sortStuff));
    const s = this.pipeline.getBindGroupLayout(3), a = this.device.createBindGroup({
      layout: s,
      entries: [
        { binding: 0, resource: { buffer: this.settingsUniforms.buffer } },
        { binding: 1, resource: { buffer: r.pointCloud.modelParamsUniforms.buffer } }
      ]
    });
    e.setBindGroup(3, a);
    const l = Math.ceil(r.pointCloud.numPoints / 256);
    e.dispatchWorkgroups(l, 1, 1), e.end();
  }
  /**
   * Get bind group layout (required by interface)
   */
  getBindGroupLayout(r) {
    return this.pipeline.getBindGroupLayout(0);
  }
  /**
   * Pack camera matrices and parameters into uniform buffer
   */
  packCameraUniforms(r, i) {
    const e = this.scratchCameraView, t = r.viewMatrix();
    e.set(t, 0);
    const o = this.invertMatrix4(t);
    e.set(o, 16);
    const n = r.projMatrix(), s = this.multiplyMatrix4(c, n);
    e.set(s, 32);
    const a = this.invertMatrix4(n);
    e.set(a, 48), e[64] = i[0], e[65] = i[1];
    const u = r.projection.focal(i);
    e[66] = u[0], e[67] = u[1], this.cameraUniforms.setData(e);
  }
  /**
   * Pack render settings into uniform buffer
   */
  packSettingsUniforms(r, i) {
    const e = this.scratchSettingsView;
    let t = 0;
    e.setFloat32(t + 0, i.clippingBoxMin[0], !0), e.setFloat32(t + 4, i.clippingBoxMin[1], !0), e.setFloat32(t + 8, i.clippingBoxMin[2], !0), e.setFloat32(t + 12, 0, !0), t += 16, e.setFloat32(t + 0, i.clippingBoxMax[0], !0), e.setFloat32(t + 4, i.clippingBoxMax[1], !0), e.setFloat32(t + 8, i.clippingBoxMax[2], !0), e.setFloat32(t + 12, 0, !0), t += 16, e.setFloat32(t, i.gaussianScaling, !0), t += 4, e.setUint32(t, i.maxSHDegree, !0), t += 4, e.setUint32(t, i.showEnvMap ? 1 : 0, !0), t += 4, e.setUint32(t, i.mipSplatting ? 1 : 0, !0), t += 4, e.setFloat32(t, i.kernelSize, !0), t += 4, e.setFloat32(t, i.walltime, !0), t += 4, e.setFloat32(t, i.sceneExtend, !0), t += 4, t = 64, e.setFloat32(t + 0, i.center[0], !0), e.setFloat32(t + 4, i.center[1], !0), e.setFloat32(t + 8, i.center[2], !0), e.setFloat32(t + 12, 0, !0), this.settingsUniforms.setData(e);
  }
  /**
   * Pack per-model params (model matrix + baseOffset + num_points)
   */
  identityMat4() {
    return new Float32Array([
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
    ]);
  }
  /**
   * Debug method to verify count values after preprocessing
   */
  async debugCountValues() {
    this._debugCountBuffer && (console.log("=== PREPROCESSOR DEBUG ==="), await d(
      this.device,
      this._debugCountBuffer,
      this.modelParamsUniforms?.buffer || null,
      this._debugMaxPoints || 0
    ));
  }
  /**
   * Get point cloud bind group layout  
   */
  getPointCloudBindGroupLayout(r) {
    return r.createBindGroupLayout({
      label: "Point Cloud Bind Group Layout",
      entries: [
        { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: "read-only-storage" } },
        // gaussians
        { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: { type: "read-only-storage" } },
        // sh coeffs
        { binding: 2, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // splat2d output
        { binding: 3, visibility: GPUShaderStage.COMPUTE, buffer: { type: "uniform" } }
        // uniforms
      ]
    });
  }
  /**
   * Get sort bind group layout
   */
  getSortBindGroupLayout(r) {
    return r.createBindGroupLayout({
      label: "Sort Preprocess Bind Group Layout",
      entries: [
        { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // sort infos
        { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // keys
        { binding: 2, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // payloads  
        { binding: 3, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } }
        // dispatch
      ]
    });
  }
  /**
   * Settings + ModelParams 合并后的 BGL（group 3）
   */
  getSettingsAndModelParamsBGL(r) {
    return r.createBindGroupLayout({
      label: "Settings + ModelParams BGL",
      entries: [
        { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: "uniform" } },
        // RenderSettings
        { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: { type: "uniform" } }
        // ModelParams
      ]
    });
  }
  /**
   * Get sort bind group from sort stuff
   */
  getSortBindGroup(r) {
    return r.sorter_bg_pre;
  }
  /**
   * Invert a 4x4 matrix
   */
  invertMatrix4(r) {
    const i = new Float32Array(16), e = r;
    i[0] = e[5] * e[10] * e[15] - e[5] * e[11] * e[14] - e[9] * e[6] * e[15] + e[9] * e[7] * e[14] + e[13] * e[6] * e[11] - e[13] * e[7] * e[10], i[4] = -e[4] * e[10] * e[15] + e[4] * e[11] * e[14] + e[8] * e[6] * e[15] - e[8] * e[7] * e[14] - e[12] * e[6] * e[11] + e[12] * e[7] * e[10], i[8] = e[4] * e[9] * e[15] - e[4] * e[11] * e[13] - e[8] * e[5] * e[15] + e[8] * e[7] * e[13] + e[12] * e[5] * e[11] - e[12] * e[7] * e[9], i[12] = -e[4] * e[9] * e[14] + e[4] * e[10] * e[13] + e[8] * e[5] * e[14] - e[8] * e[6] * e[13] - e[12] * e[5] * e[10] + e[12] * e[6] * e[9], i[1] = -e[1] * e[10] * e[15] + e[1] * e[11] * e[14] + e[9] * e[2] * e[15] - e[9] * e[3] * e[14] - e[13] * e[2] * e[11] + e[13] * e[3] * e[10], i[5] = e[0] * e[10] * e[15] - e[0] * e[11] * e[14] - e[8] * e[2] * e[15] + e[8] * e[3] * e[14] + e[12] * e[2] * e[11] - e[12] * e[3] * e[10], i[9] = -e[0] * e[9] * e[15] + e[0] * e[11] * e[13] + e[8] * e[1] * e[15] - e[8] * e[3] * e[13] - e[12] * e[1] * e[11] + e[12] * e[3] * e[9], i[13] = e[0] * e[9] * e[14] - e[0] * e[10] * e[13] - e[8] * e[1] * e[14] + e[8] * e[2] * e[13] + e[12] * e[1] * e[10] - e[12] * e[2] * e[9], i[2] = e[1] * e[6] * e[15] - e[1] * e[7] * e[14] - e[5] * e[2] * e[15] + e[5] * e[3] * e[14] + e[13] * e[2] * e[7] - e[13] * e[3] * e[6], i[6] = -e[0] * e[6] * e[15] + e[0] * e[7] * e[14] + e[4] * e[2] * e[15] - e[4] * e[3] * e[14] - e[12] * e[2] * e[7] + e[12] * e[3] * e[6], i[10] = e[0] * e[5] * e[15] - e[0] * e[7] * e[13] - e[4] * e[1] * e[15] + e[4] * e[3] * e[13] + e[12] * e[1] * e[7] - e[12] * e[3] * e[5], i[14] = -e[0] * e[5] * e[14] + e[0] * e[6] * e[13] + e[4] * e[1] * e[14] - e[4] * e[2] * e[13] - e[12] * e[1] * e[6] + e[12] * e[2] * e[5], i[3] = -e[1] * e[6] * e[11] + e[1] * e[7] * e[10] + e[5] * e[2] * e[11] - e[5] * e[3] * e[10] - e[9] * e[2] * e[7] + e[9] * e[3] * e[6], i[7] = e[0] * e[6] * e[11] - e[0] * e[7] * e[10] - e[4] * e[2] * e[11] + e[4] * e[3] * e[10] + e[8] * e[2] * e[7] - e[8] * e[3] * e[6], i[11] = -e[0] * e[5] * e[11] + e[0] * e[7] * e[9] + e[4] * e[1] * e[11] - e[4] * e[3] * e[9] - e[8] * e[1] * e[7] + e[8] * e[3] * e[5], i[15] = e[0] * e[5] * e[10] - e[0] * e[6] * e[9] - e[4] * e[1] * e[10] + e[4] * e[2] * e[9] + e[8] * e[1] * e[6] - e[8] * e[2] * e[5];
    let t = e[0] * i[0] + e[1] * i[4] + e[2] * i[8] + e[3] * i[12];
    if (Math.abs(t) < 1e-8)
      throw new Error("Matrix not invertible");
    t = 1 / t;
    for (let o = 0; o < 16; o++)
      i[o] *= t;
    return i;
  }
  /**
   * Multiply two 4x4 matrices
   */
  multiplyMatrix4(r, i) {
    const e = r, t = i, o = new Float32Array(16);
    for (let n = 0; n < 4; n++) {
      const s = e[n], a = e[n + 4], u = e[n + 8], l = e[n + 12];
      o[n] = s * t[0] + a * t[1] + u * t[2] + l * t[3], o[n + 4] = s * t[4] + a * t[5] + u * t[6] + l * t[7], o[n + 8] = s * t[8] + a * t[9] + u * t[10] + l * t[11], o[n + 12] = s * t[12] + a * t[13] + u * t[14] + l * t[15];
    }
    return o;
  }
}
export {
  g as G
};
