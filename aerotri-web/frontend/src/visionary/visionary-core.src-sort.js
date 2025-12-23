import { r as B } from "./visionary-core.src-shaders.js";
const d = 256, h = 8, l = 1 << h, y = 32 / h, f = 15, S = f, U = 128, P = 256;
function R(m) {
  const e = m.slice();
  for (let t = e.length - 1; t > 0; t--) {
    const r = Math.floor(Math.random() * (t + 1));
    [e[t], e[r]] = [e[r], e[t]];
  }
  return e;
}
class g {
  bindGroupLayout;
  renderBindGroupLayout;
  preprocessBindGroupLayout;
  zero_p;
  histogram_p;
  prefix_p;
  scatter_even_p;
  scatter_odd_p;
  subgroupSize;
  // Private constructor to be called by the async factory method.
  constructor() {
  }
  /**
   * Asynchronously creates and initializes a new GPURSSorter.
   * This factory pattern is used because the constructor needs to be async.
   * It determines the best subgroup size by testing various configurations.
   */
  static async create(e, t) {
    console.debug("Searching for the maximum subgroup size...");
    const r = [16, 32, 16, 8, 1];
    for (const s of r) {
      console.debug(`Testing sorting with subgroup size ${s}`);
      try {
        const a = new g();
        if (await a.initializeWithSubgroupSize(e, s), await a.testSort(e, t))
          return console.log(`Subgroup size ${s} works.`), a;
      } catch (a) {
        console.warn(`Subgroup size ${s} failed during pipeline creation or test run.`, a);
      }
    }
    throw new Error("GPURSSorter::create() No working subgroup size was found. Unable to use sorter.");
  }
  /**
   * Initializes the sorter's pipelines and layouts for a given subgroup size.
   */
  async initializeWithSubgroupSize(e, t) {
    this.subgroupSize = t, this.bindGroupLayout = this.createBindGroupLayout(e), this.renderBindGroupLayout = g.createRenderBindGroupLayout(e), this.preprocessBindGroupLayout = g.createPreprocessBindGroupLayout(e);
    const r = e.createPipelineLayout({
      label: "radix sort pipeline layout",
      bindGroupLayouts: [this.bindGroupLayout]
    }), s = this.processShaderTemplate(B), a = e.createShaderModule({
      label: "Radix sort shader",
      code: s
    });
    this.zero_p = await e.createComputePipelineAsync({
      label: "Zero the histograms",
      layout: r,
      compute: { module: a, entryPoint: "zero_histograms" }
    }), this.histogram_p = await e.createComputePipelineAsync({
      label: "calculate_histogram",
      layout: r,
      compute: { module: a, entryPoint: "calculate_histogram" }
    }), this.prefix_p = await e.createComputePipelineAsync({
      label: "prefix_histogram",
      layout: r,
      compute: { module: a, entryPoint: "prefix_histogram" }
    }), this.scatter_even_p = await e.createComputePipelineAsync({
      label: "scatter_even",
      layout: r,
      compute: { module: a, entryPoint: "scatter_even" }
    }), this.scatter_odd_p = await e.createComputePipelineAsync({
      label: "scatter_odd",
      layout: r,
      compute: { module: a, entryPoint: "scatter_odd" }
    });
  }
  processShaderTemplate(e) {
    const t = Math.max(1, this.subgroupSize | 0), r = Math.floor(l / t), s = Math.floor(r / t), i = l + S * P, o = 0, u = o + r, n = u + s, c = `const histogram_sg_size: u32 = ${t}u;
            const histogram_wg_size: u32 = ${d}u;
            const rs_radix_log2: u32 = ${h}u;
            const rs_radix_size: u32 = ${l}u;
            const rs_keyval_size: u32 = ${y}u;
            const rs_histogram_block_rows: u32 = ${f}u;
            const rs_scatter_block_rows: u32 = ${S}u;
            const rs_mem_dwords: u32 = ${i}u;
            const rs_mem_sweep_0_offset: u32 = ${o}u;
            const rs_mem_sweep_1_offset: u32 = ${u}u;
            const rs_mem_sweep_2_offset: u32 = ${n}u;
            `;
    let p = e.replace(/{histogram_wg_size}/g, d.toString()).replace(/{prefix_wg_size}/g, U.toString()).replace(/{scatter_wg_size}/g, P.toString());
    return c + p;
  }
  /**
   * Runs a small test sort to verify the current configuration works.
   */
  async testSort(e, t) {
    const s = new Float32Array(
      R(Array.from({ length: 8192 }, (n, c) => 8191 - c))
    ), a = new Float32Array(
      Array.from({ length: 8192 }, (n, c) => c)
    ), i = this.createSortStuff(e, 8192);
    t.writeBuffer(i.key_a, 0, s.buffer);
    const o = e.createCommandEncoder({ label: "GPURSSorter test_sort" });
    this.recordSort(i, 8192, o), t.submit([o.finish()]), await e.queue.onSubmittedWorkDone();
    const u = await this.downloadBuffer(e, t, i.key_a, "f32");
    for (let n = 0; n < 8192; n++)
      if (u[n] !== a[n])
        return console.error(`Sort failed at index ${n}. Expected ${a[n]}, got ${u[n]}`), !1;
    return !0;
  }
  /**
   * Creates all the necessary buffers and bind groups for sorting a given number of points.
   */
  createSortStuff(e, t) {
    const { key_a: r, key_b: s, payload_a: a, payload_b: i } = this.createKeyvalBuffers(e, t, 4), o = this.createInternalMemBuffer(e, t), { sorter_uni: u, sorter_dis: n, sorter_bg: c } = this.createBindGroup(
      e,
      t,
      o,
      r,
      s,
      a,
      i
    ), p = this.createRenderBindGroup(e, u, a), _ = this.createPreprocessBindGroup(e, u, n, r, a);
    return {
      numPoints: t,
      num_points: t,
      // Compatibility field for renderer
      sortedIndices: a,
      // payload_a contains the sorted indices
      indirectBuffer: n,
      sorter_uni: u,
      sorter_dis: n,
      sorter_bg: c,
      sorter_render_bg: p,
      sorter_bg_pre: _,
      internal_mem: o,
      key_a: r,
      key_b: s,
      payload_a: a,
      payload_b: i
    };
  }
  recordSort(e, t, r) {
    const s = e, a = 4;
    this.recordCalculateHistogram(s.sorter_bg, t, r), this.recordPrefixHistogram(s.sorter_bg, a, r), this.recordScatterKeys(s.sorter_bg, a, t, r);
  }
  recordSortIndirect_one(e, t, r) {
    const s = e, a = 4, i = r.beginComputePass({ label: "Radix Sort :: Indirect Histogram Pass" });
    i.setBindGroup(0, s.sorter_bg), i.setPipeline(this.zero_p), i.dispatchWorkgroupsIndirect(t, 0), i.setPipeline(this.histogram_p), i.dispatchWorkgroupsIndirect(t, 0), i.end(), this.recordPrefixHistogram(s.sorter_bg, a, r);
    const o = r.beginComputePass({ label: "Radix Sort :: Indirect Scatter Pass" });
    o.setBindGroup(0, s.sorter_bg), o.setPipeline(this.scatter_even_p), o.dispatchWorkgroupsIndirect(t, 0), o.setPipeline(this.scatter_odd_p), o.dispatchWorkgroupsIndirect(t, 0), o.setPipeline(this.scatter_even_p), o.dispatchWorkgroupsIndirect(t, 0), o.setPipeline(this.scatter_odd_p), o.dispatchWorkgroupsIndirect(t, 0), o.end();
  }
  recordSortIndirect(e, t, r) {
    const s = e, a = 4;
    {
      const o = r.beginComputePass({ label: "RS::Zero (Indirect)" });
      o.setBindGroup(0, s.sorter_bg), o.setPipeline(this.zero_p), o.dispatchWorkgroupsIndirect(t, 0), o.end();
    }
    {
      const o = r.beginComputePass({ label: "RS::Histogram (Indirect)" });
      o.setBindGroup(0, s.sorter_bg), o.setPipeline(this.histogram_p), o.dispatchWorkgroupsIndirect(t, 0), o.end();
    }
    this.recordPrefixHistogram(s.sorter_bg, a, r);
    const i = (o, u) => {
      const n = r.beginComputePass({ label: u });
      n.setBindGroup(0, s.sorter_bg), n.setPipeline(o), n.dispatchWorkgroupsIndirect(t, 0), n.end();
    };
    i(this.scatter_even_p, "RS::Scatter0_even (Indirect)"), i(this.scatter_odd_p, "RS::Scatter1_odd (Indirect)"), i(this.scatter_even_p, "RS::Scatter2_even (Indirect)"), i(this.scatter_odd_p, "RS::Scatter3_odd (Indirect)");
  }
  // Static methods for bind group layouts
  static createRenderBindGroupLayout(e) {
    return e.createBindGroupLayout({
      label: "Radix Sort Render Bind Group Layout",
      entries: [
        { binding: 0, visibility: GPUShaderStage.COMPUTE | GPUShaderStage.VERTEX, buffer: { type: "read-only-storage" } },
        // infos
        { binding: 4, visibility: GPUShaderStage.COMPUTE | GPUShaderStage.VERTEX, buffer: { type: "read-only-storage" } }
        // payload_a
      ]
    });
  }
  static createPreprocessBindGroupLayout(e) {
    return e.createBindGroupLayout({
      label: "Radix Sort Preprocess Bind Group Layout",
      entries: [
        { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // infos
        { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // keyval_a
        { binding: 2, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // payload_a
        { binding: 3, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } }
        // dispatch_buffer
      ]
    });
  }
  recordResetIndirectBuffer(e, t, r) {
    const s = new Uint32Array([0]);
    r.writeBuffer(e, 0, s), r.writeBuffer(t, 0, s);
  }
  // Private implementation methods (remaining methods from original implementation)
  createBindGroupLayout(e) {
    return e.createBindGroupLayout({
      label: "Radix Sort Bind Group Layout",
      entries: [
        { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // infos
        { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // histograms
        { binding: 2, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // keys
        { binding: 3, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // keys_b
        { binding: 4, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } },
        // payload_a
        { binding: 5, visibility: GPUShaderStage.COMPUTE, buffer: { type: "storage" } }
        // payload_b
      ]
    });
  }
  getScatterHistogramSizes(e) {
    const t = d * S, r = Math.ceil(e / t), s = r * t, a = d * f, o = Math.ceil(s / a) * a;
    return { scatter_blocks_ru: r, count_ru_histo: o };
  }
  createKeyvalBuffers(e, t, r) {
    const s = d * f, i = (Math.floor((t + s) / s) + 1) * s * Float32Array.BYTES_PER_ELEMENT, o = e.createBuffer({
      label: "Radix data buffer a",
      size: i,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC
    }), u = e.createBuffer({
      label: "Radix data buffer b",
      size: i,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC
    });
    r !== 4 && console.warn("Currently only 4-byte payloads are fully supported, matching the original Rust implementation.");
    const n = Math.max(1, t * r), c = e.createBuffer({
      label: "Radix payload buffer a",
      size: n,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC
    }), p = e.createBuffer({
      label: "Radix payload buffer b",
      size: n,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC
    });
    return { key_a: o, key_b: u, payload_a: c, payload_b: p };
  }
  createInternalMemBuffer(e, t) {
    const { scatter_blocks_ru: r } = this.getScatterHistogramSizes(t), s = l * Uint32Array.BYTES_PER_ELEMENT, a = (y + r - 1 + 1) * s;
    return e.createBuffer({
      label: "Internal radix sort buffer",
      size: a,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC
    });
  }
  createBindGroup(e, t, r, s, a, i, o) {
    const { scatter_blocks_ru: u, count_ru_histo: n } = this.getScatterHistogramSizes(t), c = {
      keys_size: t,
      padded_size: n,
      passes: 4,
      even_pass: 0,
      odd_pass: 0
    }, p = e.createBuffer({
      label: "Radix uniform buffer",
      size: 5 * Uint32Array.BYTES_PER_ELEMENT,
      // GeneralInfo has 5 u32 fields
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC,
      mappedAtCreation: !0
    });
    new Uint32Array(p.getMappedRange()).set([
      c.keys_size,
      c.padded_size,
      c.passes,
      c.even_pass,
      c.odd_pass
    ]), p.unmap();
    const _ = {
      dispatch_x: u,
      dispatch_y: 1,
      dispatch_z: 1
    }, b = e.createBuffer({
      label: "Dispatch indirect buffer",
      size: 3 * Uint32Array.BYTES_PER_ELEMENT,
      // IndirectDispatch has 3 u32 fields
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.INDIRECT,
      mappedAtCreation: !0
    });
    new Uint32Array(b.getMappedRange()).set([
      _.dispatch_x,
      _.dispatch_y,
      _.dispatch_z
    ]), b.unmap();
    const G = e.createBindGroup({
      label: "Radix bind group",
      layout: this.bindGroupLayout,
      entries: [
        { binding: 0, resource: { buffer: p } },
        { binding: 1, resource: { buffer: r } },
        { binding: 2, resource: { buffer: s } },
        { binding: 3, resource: { buffer: a } },
        { binding: 4, resource: { buffer: i } },
        { binding: 5, resource: { buffer: o } }
      ]
    });
    return { sorter_uni: p, sorter_dis: b, sorter_bg: G };
  }
  createRenderBindGroup(e, t, r) {
    return e.createBindGroup({
      label: "Render bind group",
      layout: this.renderBindGroupLayout,
      entries: [
        { binding: 0, resource: { buffer: t } },
        { binding: 4, resource: { buffer: r } }
      ]
    });
  }
  createPreprocessBindGroup(e, t, r, s, a) {
    return e.createBindGroup({
      label: "Preprocess bind group",
      layout: this.preprocessBindGroupLayout,
      entries: [
        { binding: 0, resource: { buffer: t } },
        { binding: 1, resource: { buffer: s } },
        { binding: 2, resource: { buffer: a } },
        { binding: 3, resource: { buffer: r } }
      ]
    });
  }
  // private recordCalculateHistogram(bind_group: GPUBindGroup, keysize: number, encoder: GPUCommandEncoder) {
  //     const { count_ru_histo } = this.getScatterHistogramSizes(keysize);
  //     const histo_block_kvs = HISTOGRAM_WG_SIZE * RS_HISTOGRAM_BLOCK_ROWS;
  //     const hist_blocks_ru = Math.ceil(count_ru_histo / histo_block_kvs);
  //     const pass = encoder.beginComputePass({ label: "Radix Sort :: Histogram Pass" });
  //     pass.setBindGroup(0, bind_group);
  //     // Zero histograms
  //     pass.setPipeline(this.zero_p);
  //     pass.dispatchWorkgroups(hist_blocks_ru, 1, 1);
  //     // Calculate histograms
  //     pass.setPipeline(this.histogram_p);
  //     pass.setBindGroup(0, bind_group);
  //     pass.dispatchWorkgroups(hist_blocks_ru, 1, 1);
  //     pass.end();
  // }
  recordCalculateHistogram(e, t, r) {
    const { count_ru_histo: s } = this.getScatterHistogramSizes(t), a = d * f, i = Math.ceil(s / a);
    {
      const o = r.beginComputePass({ label: "RS::Zero" });
      o.setBindGroup(0, e), o.setPipeline(this.zero_p), o.dispatchWorkgroups(i, 1, 1), o.end();
    }
    {
      const o = r.beginComputePass({ label: "RS::Histogram" });
      o.setBindGroup(0, e), o.setPipeline(this.histogram_p), o.dispatchWorkgroups(i, 1, 1), o.end();
    }
  }
  recordPrefixHistogram(e, t, r) {
    const s = r.beginComputePass({ label: "Radix Sort :: Prefix Sum Pass" });
    s.setPipeline(this.prefix_p), s.setBindGroup(0, e), s.dispatchWorkgroups(t, 1, 1), s.end();
  }
  recordScatterKeys(e, t, r, s) {
    if (t !== 4) throw new Error("Only 4 passes are supported for 32-bit keys.");
    const { scatter_blocks_ru: a } = this.getScatterHistogramSizes(r), i = (o, u) => {
      const n = s.beginComputePass({ label: u });
      n.setBindGroup(0, e), n.setPipeline(o), n.dispatchWorkgroups(a, 1, 1), n.end();
    };
    i(this.scatter_even_p, "RS::Scatter0_even"), i(this.scatter_odd_p, "RS::Scatter1_odd"), i(this.scatter_even_p, "RS::Scatter2_even"), i(this.scatter_odd_p, "RS::Scatter3_odd");
  }
  /**
   * Helper function to download buffer data from the GPU.
   */
  async downloadBuffer(e, t, r, s) {
    const a = e.createBuffer({
      label: "Download buffer",
      size: r.size,
      usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST
    }), i = e.createCommandEncoder({ label: "Copy encoder" });
    i.copyBufferToBuffer(r, 0, a, 0, r.size), t.submit([i.finish()]), await a.mapAsync(GPUMapMode.READ);
    const o = a.getMappedRange();
    let u;
    return s === "f32" ? u = new Float32Array(o.slice(0)) : u = new Uint32Array(o.slice(0)), a.unmap(), a.destroy(), u;
  }
}
export {
  g as G
};
