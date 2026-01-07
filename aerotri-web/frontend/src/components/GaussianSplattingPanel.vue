<template>
  <div class="gs-panel" v-if="block">
    <!-- 顶部状态和快速操作区 -->
    <div class="gs-header">
      <div class="status-section">
        <div class="status-line">
          <span class="status-label">3DGS 状态：</span>
          <el-tag :type="statusTagType" size="large">{{ statusText }}</el-tag>
          <span v-if="currentStageLabel" class="stage-label">{{ currentStageLabel }}</span>
        </div>
        <div class="status-progress">
          <el-progress
            :percentage="Math.round(state.progress)"
            :stroke-width="20"
            :text-inside="true"
            :status="progressStatus"
          />
        </div>
      </div>

      <div class="quick-actions">
        <div class="quick-params">
          <div class="param-group">
            <span class="param-label">迭代次数</span>
            <el-input-number v-model="params.iterations" :min="1" :step="1000" size="small" />
          </div>
          <div class="param-group">
            <span class="param-label">分辨率</span>
            <el-input-number v-model="params.resolution" :min="-1" :max="8" size="small" />
          </div>
          <div class="param-group">
            <span class="param-label">数据设备</span>
            <el-select v-model="params.data_device" size="small" style="width: 90px">
              <el-option label="cpu" value="cpu" />
              <el-option label="cuda" value="cuda" />
            </el-select>
          </div>
          <div class="param-group">
            <span class="param-label">SH 阶数</span>
            <el-input-number v-model="params.sh_degree" :min="0" :max="3" size="small" />
          </div>
        </div>
        <div class="action-buttons">
          <el-button
            v-if="isRunning"
            type="danger"
            :loading="loadingAction"
            @click="onCancel"
            size="default"
          >
            <el-icon><VideoPause /></el-icon>
            中止训练
          </el-button>
          <el-button
            v-else
            type="primary"
            :loading="loadingAction"
            :disabled="!canStart"
            @click="onStart"
            size="default"
          >
            <el-icon><VideoPlay /></el-icon>
            开始训练
          </el-button>
        </div>
      </div>
    </div>

    <!-- GPU资源选择区（独立卡片，显眼位置） -->
    <el-card class="gpu-resource-card">
      <template #header>
        <div class="card-header">
          <div class="card-title-group">
            <el-icon class="card-icon"><Cpu /></el-icon>
            <span>GPU 资源选择</span>
            <el-tag v-if="isRunning" type="info" size="small" effect="plain">训练中自动刷新</el-tag>
          </div>
        </div>
      </template>
      <GPUSelector v-model="gpuIndex" />
    </el-card>

    <!-- 内容标签页区 -->
    <el-tabs v-model="activeTab" class="gs-content-tabs">
      <!-- 参数配置标签页 -->
      <el-tab-pane label="参数配置" name="params">
        <el-card class="params-card">
          <template #header>
            <div class="card-header">
              <span>训练参数配置</span>
            </div>
          </template>
          <div class="params-content">
            <div class="params-section">
              <h4 class="section-title">基础参数</h4>
              <div class="params-grid">
                <div class="param-item">
                  <label>迭代次数</label>
                  <el-input-number v-model="params.iterations" :min="1" :step="1000" />
                </div>
                <div class="param-item">
                  <label>分辨率</label>
                  <el-input-number v-model="params.resolution" :min="-1" :max="8" />
                  <el-text type="info" size="small">-1表示使用原始分辨率</el-text>
                </div>
                <div class="param-item">
                  <label>数据设备</label>
                  <el-select v-model="params.data_device" style="width: 120px">
                    <el-option label="cpu" value="cpu" />
                    <el-option label="cuda" value="cuda" />
                  </el-select>
                </div>
                <div class="param-item">
                  <label>SH 阶数</label>
                  <el-input-number v-model="params.sh_degree" :min="0" :max="3" />
                </div>
              </div>
            </div>

            <el-divider />

            <div class="params-section">
              <el-collapse v-model="advancedParamsExpanded">
                <el-collapse-item title="高级参数" name="advanced">
                  <div class="advanced-params-grid">
                    <div class="param-row">
                      <label>学习率参数</label>
                      <div class="param-inputs">
                        <el-input-number v-model="params.position_lr_init" :min="0" :step="0.00001" :precision="5" size="small" placeholder="初始位置LR" />
                        <el-input-number v-model="params.position_lr_final" :min="0" :step="0.00001" :precision="5" size="small" placeholder="最终位置LR" />
                        <el-input-number v-model="params.feature_lr" :min="0" :step="0.0001" :precision="4" size="small" placeholder="特征LR" />
                        <el-input-number v-model="params.opacity_lr" :min="0" :step="0.001" :precision="3" size="small" placeholder="不透明度LR" />
                        <el-input-number v-model="params.scaling_lr" :min="0" :step="0.001" :precision="3" size="small" placeholder="缩放LR" />
                        <el-input-number v-model="params.rotation_lr" :min="0" :step="0.0001" :precision="4" size="small" placeholder="旋转LR" />
                      </div>
                    </div>
                    <div class="param-row">
                      <label>优化参数</label>
                      <div class="param-inputs">
                        <el-input-number v-model="params.lambda_dssim" :min="0" :max="1" :step="0.01" :precision="2" size="small" placeholder="DSSIM权重" />
                        <el-input-number v-model="params.percent_dense" :min="0" :max="1" :step="0.001" :precision="3" size="small" placeholder="密集化比例" />
                        <el-input-number v-model="params.densification_interval" :min="1" :step="10" size="small" placeholder="密集化间隔" />
                        <el-input-number v-model="params.opacity_reset_interval" :min="1" :step="100" size="small" placeholder="不透明度重置间隔" />
                        <el-input-number v-model="params.densify_from_iter" :min="0" :step="100" size="small" placeholder="密集化起始迭代" />
                        <el-input-number v-model="params.densify_until_iter" :min="0" :step="1000" size="small" placeholder="密集化结束迭代" />
                        <el-input-number v-model="params.densify_grad_threshold" :min="0" :step="0.0001" :precision="4" size="small" placeholder="密集化梯度阈值" />
                      </div>
                    </div>
                    <div class="param-row">
                      <label>其他选项</label>
                      <div class="param-checkboxes">
                        <el-checkbox v-model="params.white_background">白色背景</el-checkbox>
                        <el-checkbox v-model="params.random_background">随机背景</el-checkbox>
                        <el-checkbox v-model="params.quiet">静默模式</el-checkbox>
                        <el-checkbox v-model="params.disable_viewer">禁用查看器</el-checkbox>
                        <el-checkbox v-model="params.export_spz_on_complete">训练完成后导出 SPZ</el-checkbox>
                      </div>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 训练监控标签页 -->
      <el-tab-pane label="训练监控" name="monitor">
        <el-card class="tensorboard-card" v-if="tensorboardUrl">
          <template #header>
            <div class="card-header">
              <div class="card-title-group">
                <el-icon class="card-icon"><DataAnalysis /></el-icon>
                <span>TensorBoard 训练指标</span>
                <el-tag v-if="isRunning" type="success" size="small" effect="plain">实时更新</el-tag>
              </div>
              <div class="card-actions">
                <el-button text size="small" @click="refreshStatus">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
                <el-button text size="small" type="primary" @click="openTensorBoardFullscreen">
                  <el-icon><FullScreen /></el-icon>
                  全屏查看
                </el-button>
                <el-button text size="small" @click="openTensorBoardNewWindow">
                  <el-icon><Link /></el-icon>
                  新窗口
                </el-button>
              </div>
            </div>
          </template>
          <div class="tensorboard-container">
            <div class="tensorboard-preview">
              <iframe
                :src="tensorboardUrl"
                class="tensorboard-iframe"
                frameborder="0"
                allowfullscreen
                title="TensorBoard 训练指标"
              />
            </div>
            <div class="tensorboard-tips">
              <el-alert
                type="info"
                :closable="false"
                show-icon
              >
                <template #default>
                  <span>提示：点击"全屏查看"或"新窗口"按钮可获得更好的查看体验</span>
                </template>
              </el-alert>
            </div>
          </div>
        </el-card>
        <el-empty v-else description="TensorBoard 未启动，训练开始后会自动显示" />
      </el-tab-pane>

      <!-- 训练产物标签页 -->
      <el-tab-pane label="训练产物" name="outputs">
        <el-card class="files-card">
          <template #header>
            <div class="card-header">
              <span>训练产物</span>
              <div class="card-header-actions">
                <el-button
                  v-if="latestSpzFile"
                  type="primary"
                  size="small"
                  @click="openSpzPreviewDialog"
                >
                  <el-icon><FullScreen /></el-icon>
                  在 Visionary 中预览 SPZ
                </el-button>
                <el-button
                  size="small"
                  :disabled="!latestPreviewableFile"
                  @click="openLatestPreviewInNewTab"
                >
                  <el-icon><Link /></el-icon>
                  在新标签页中使用 Visionary
                </el-button>
                <el-button text size="small" @click="refreshAll">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </div>
          </template>
          <el-table :data="state.files" size="small" style="width: 100%">
            <el-table-column prop="name" label="文件" min-width="240" />
            <el-table-column prop="type" label="类型" width="110" />
            <el-table-column prop="size_bytes" label="大小" width="120">
              <template #default="{ row }">
                {{ formatSize(row.size_bytes) }}
              </template>
            </el-table-column>
            <el-table-column prop="mtime" label="更新时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.mtime) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button
                  v-if="row.preview_supported && row.name.endsWith('.spz')"
                  type="primary"
                  text
                  size="small"
                  @click="openSpzPreviewDialog(row)"
                >
                  预览 (SPZ)
                </el-button>
                <el-button
                  v-if="row.preview_supported"
                  text
                  size="small"
                  @click="openPreviewInNewTab(row)"
                >
                  <el-icon><Link /></el-icon>
                  在新标签页中打开
                </el-button>
                <el-button 
                  type="primary" 
                  text 
                  size="small" 
                  :loading="downloadingFiles[row.name]"
                  @click="downloadFile(row)"
                >
                  下载
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="state.files.length === 0" class="empty">
            <el-text type="info">尚未生成输出</el-text>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 3D Tiles 转换标签页 -->
      <el-tab-pane label="3D Tiles 转换" name="tiles">
        <el-card class="tiles-card">
          <template #header>
            <div class="card-header">
              <span>3D Tiles 转换</span>
              <div class="card-actions">
                <el-button
                  text
                  size="small"
                  @click="refreshTilesStatus"
                  :loading="loadingTilesStatus"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新状态
                </el-button>
              </div>
            </div>
          </template>
          <div class="tiles-content">
            <!-- 转换状态 -->
            <div class="tiles-status-section">
              <div class="status-line">
                <span class="status-label">转换状态：</span>
                <el-tag :type="tilesStatusTagType" size="large">{{ tilesStatusText }}</el-tag>
                <span v-if="tilesCurrentStage" class="stage-label">{{ tilesCurrentStage }}</span>
              </div>
              <div class="status-progress" v-if="tilesStatus === 'RUNNING' || tilesStatus === 'COMPLETED'">
                <el-progress
                  :percentage="Math.round(tilesProgress)"
                  :stroke-width="20"
                  :text-inside="true"
                  :status="tilesProgressStatus"
                />
              </div>
              <div v-if="tilesError" class="error-message">
                <el-alert :title="tilesError" type="error" :closable="false" />
              </div>
            </div>

            <!-- 转换操作 -->
            <div class="tiles-actions-section">
              <el-form :model="tilesConvertParams" label-width="120px" size="default">
                <el-form-item label="迭代版本">
                  <el-select v-model="tilesConvertParams.iteration" placeholder="选择迭代版本" clearable>
                    <el-option
                      v-for="iter in availableIterations"
                      :key="iter"
                      :label="`iteration_${iter}`"
                      :value="iter"
                    />
                  </el-select>
                  <el-text type="info" style="margin-left: 8px">
                    留空则使用最新迭代版本
                  </el-text>
                </el-form-item>
                <el-form-item label="SPZ 压缩">
                  <el-switch v-model="tilesConvertParams.use_spz" />
                  <el-text type="info" style="margin-left: 8px">
                    启用后可减少约 90% 文件大小
                  </el-text>
                </el-form-item>
              </el-form>
              <div class="action-buttons">
                <el-button
                  v-if="tilesStatus === 'RUNNING'"
                  type="danger"
                  :loading="loadingTilesAction"
                  @click="onCancelTilesConversion"
                >
                  <el-icon><VideoPause /></el-icon>
                  取消转换
                </el-button>
                <el-button
                  v-else
                  type="primary"
                  :loading="loadingTilesAction"
                  :disabled="!canStartTilesConversion"
                  @click="onStartTilesConversion"
                >
                  <el-icon><VideoPlay /></el-icon>
                  开始转换
                </el-button>
              </div>
            </div>

            <!-- 转换文件列表 -->
            <div class="tiles-files-section" v-if="tilesFiles.length > 0">
              <h4 class="section-title">转换结果文件</h4>
              <el-table :data="tilesFiles" size="small" style="width: 100%">
                <el-table-column prop="name" label="文件" min-width="240" />
                <el-table-column prop="type" label="类型" width="110" />
                <el-table-column prop="size_bytes" label="大小" width="120">
                  <template #default="{ row }">
                    {{ formatSize(row.size_bytes) }}
                  </template>
                </el-table-column>
                <el-table-column prop="mtime" label="更新时间" width="180">
                  <template #default="{ row }">
                    {{ formatTime(row.mtime) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="180">
                  <template #default="{ row }">
                    <el-button
                      v-if="row.preview_supported && row.name === 'tileset.json'"
                      type="primary"
                      text
                      size="small"
                      @click="openCesiumPreview(row)"
                    >
                      Cesium 预览
                    </el-button>
                    <el-button 
                      type="primary" 
                      text 
                      size="small" 
                      :loading="downloadingTilesFiles[row.name]"
                      @click="downloadTilesFile(row)"
                    >
                      下载
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 训练日志标签页 -->
      <el-tab-pane label="训练日志" name="logs">
        <el-card class="log-card">
          <template #header>
            <div class="log-header">
              <span>训练日志</span>
              <div class="log-actions">
                <el-button text size="small" @click="toggleLog">
                  {{ showLog ? '收起' : '展开' }}
                </el-button>
                <el-button text size="small" @click="refreshLog">
                  <el-icon><Refresh /></el-icon>
                  手动刷新
                </el-button>
              </div>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="showLog" class="log-content">
              <el-scrollbar height="500px">
                <pre class="log-text">{{ logText }}</pre>
              </el-scrollbar>
            </div>
          </el-collapse-transition>
        </el-card>

        <div class="error-section" v-if="block.gs_error_message">
          <el-card>
            <template #header>
              <span style="color: var(--el-color-danger)">最近错误</span>
            </template>
            <pre class="error-box">{{ block.gs_error_message }}</pre>
          </el-card>
        </div>

        <div class="debug-section" v-if="block">
          <el-card>
            <template #header>
              <span>调试信息</span>
            </template>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="Block ID">
                <code>{{ block.id }}</code>
              </el-descriptions-item>
              <el-descriptions-item label="SfM 输出目录">
                <code>{{ block.output_path || '暂无（尚未运行空三）' }}</code>
              </el-descriptions-item>
              <el-descriptions-item label="3DGS 输出目录">
                <code>{{ block.gs_output_path || '暂无（尚未训练）' }}</code>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>


    <!-- Visionary SPZ 内嵌预览对话框（谨慎版，仅加载 SPZ） -->
    <el-dialog
      v-model="spzPreviewVisible"
      :title="spzPreviewTitle"
      width="80%"
      top="3vh"
      destroy-on-close
    >
      <div class="preview-wrap">
        <iframe v-if="spzPreviewUrl" class="preview-iframe" :src="spzPreviewUrl" />
      </div>
    </el-dialog>

    <!-- TensorBoard 全屏对话框 -->
    <el-dialog
      v-model="tensorboardFullscreenVisible"
      title="TensorBoard 训练指标"
      width="95%"
      top="2vh"
      destroy-on-close
      class="tensorboard-dialog"
    >
      <template #header>
        <div class="dialog-header">
          <div class="dialog-title-group">
            <el-icon class="dialog-icon"><DataAnalysis /></el-icon>
            <span>TensorBoard 训练指标</span>
            <el-tag v-if="isRunning" type="success" size="small" effect="plain">实时更新</el-tag>
          </div>
          <div class="dialog-actions">
            <el-button text size="small" @click="refreshStatus">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button text size="small" @click="openTensorBoardNewWindow">
              <el-icon><Link /></el-icon>
              新窗口
            </el-button>
          </div>
        </div>
      </template>
      <div class="tensorboard-fullscreen-container">
        <iframe
          v-if="tensorboardUrl"
          :src="tensorboardUrl"
          class="tensorboard-fullscreen-iframe"
          frameborder="0"
          allowfullscreen
          title="TensorBoard 训练指标"
        />
      </div>
    </el-dialog>

    <!-- Cesium 预览对话框 -->
    <el-dialog v-model="cesiumPreviewVisible" title="3DGS 预览 (Cesium)" width="90%" top="2vh" destroy-on-close>
      <div class="cesium-preview-wrap">
        <CesiumViewer v-if="cesiumTilesetUrl" :tileset-url="cesiumTilesetUrl" />
        <div v-else class="cesium-loading">
          <el-text>正在加载 tileset...</el-text>
        </div>
      </div>
    </el-dialog>

    <!-- 下载进度对话框 -->
    <el-dialog
      v-model="currentDownloadDialogVisible"
      :title="currentDownloadDialogTitle"
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div style="padding: 20px">
        <el-progress
          :percentage="currentDownloadProgress"
          :status="currentDownloadStatus"
        />
        <div style="margin-top: 10px; text-align: center; color: #909399; font-size: 12px">
          {{ currentDownloadStatus === 'success' ? '下载完成' : '正在下载...' }}
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Refresh, FullScreen, Link, Cpu, VideoPlay, VideoPause } from '@element-plus/icons-vue'
import type { Block, GSFileInfo, GSState } from '@/types'
import { gsApi, gsTilesApi } from '@/api'
import GPUSelector from './GPUSelector.vue'
import CesiumViewer from './CesiumViewer.vue'

const props = defineProps<{
  block: Block
}>()

const gpuIndex = ref(0)
const loadingAction = ref(false)
const showLog = ref(true)
const logLines = ref<string[]>([])
let logTimer: number | null = null
let statusTimer: number | null = null

const params = ref({
  // Basic parameters - 与 gaussian-splatting 源码默认值一致
  iterations: 30000,  // OptimizationParams.iterations = 30_000
  resolution: -1,  // ModelParams._resolution = -1 (使用原始分辨率)
  data_device: 'cuda' as 'cpu' | 'cuda',  // ModelParams.data_device = "cuda"
  sh_degree: 3,  // ModelParams.sh_degree = 3
  
  // Optimization parameters - 与 OptimizationParams 默认值一致
  position_lr_init: 0.00016,  // OptimizationParams.position_lr_init = 0.00016
  position_lr_final: 0.0000016,  // OptimizationParams.position_lr_final = 0.0000016
  position_lr_delay_mult: 0.01,  // OptimizationParams.position_lr_delay_mult = 0.01
  position_lr_max_steps: 30000,  // OptimizationParams.position_lr_max_steps = 30_000
  feature_lr: 0.0025,  // OptimizationParams.feature_lr = 0.0025
  opacity_lr: 0.025,  // OptimizationParams.opacity_lr = 0.025
  scaling_lr: 0.005,  // OptimizationParams.scaling_lr = 0.005
  rotation_lr: 0.001,  // OptimizationParams.rotation_lr = 0.001
  lambda_dssim: 0.2,  // OptimizationParams.lambda_dssim = 0.2
  percent_dense: 0.01,  // OptimizationParams.percent_dense = 0.01
  densification_interval: 100,  // OptimizationParams.densification_interval = 100
  opacity_reset_interval: 3000,  // OptimizationParams.opacity_reset_interval = 3000
  densify_from_iter: 500,  // OptimizationParams.densify_from_iter = 500
  densify_until_iter: 15000,  // OptimizationParams.densify_until_iter = 15_000
  densify_grad_threshold: 0.0002,  // OptimizationParams.densify_grad_threshold = 0.0002
  
  // Advanced parameters - 与源码默认值一致
  white_background: false,  // ModelParams._white_background = False
  random_background: false,  // OptimizationParams.random_background = False
  test_iterations: [7000, 30000] as number[],  // train.py default: [7_000, 30_000]
  save_iterations: [7000, 30000] as number[],  // train.py default: [7_000, 30_000]
  checkpoint_iterations: [] as number[],  // train.py default: []
  quiet: false,  // train.py default: False (action="store_true")
  disable_viewer: false,  // train.py default: False (action="store_true")
  // Export options
  export_spz_on_complete: false,
})

const advancedParamsExpanded = ref<string[]>([])

const state = ref<GSState>({
  status: (props.block.gs_status as GSState['status']) ?? 'NOT_STARTED',
  progress: props.block.gs_progress ?? 0,
  currentStage: props.block.gs_current_stage ?? null,
  files: [],
})

const tensorboardUrl = ref<string | null>(null)
const tensorboardFullscreenVisible = ref(false)
const activeTab = ref('params') // 默认显示参数配置标签页

const isRunning = computed(() => state.value.status === 'RUNNING')

const canStart = computed(() => {
  return ['NOT_STARTED', 'FAILED', 'CANCELLED', 'COMPLETED'].includes(state.value.status)
})

const statusTagType = computed(() => {
  switch (state.value.status) {
    case 'COMPLETED':
      return 'success'
    case 'RUNNING':
      return 'primary'
    case 'FAILED':
      return 'danger'
    case 'CANCELLED':
      return 'warning'
    default:
      return 'info'
  }
})

const statusText = computed(() => {
  switch (state.value.status) {
    case 'NOT_STARTED':
      return '未开始'
    case 'RUNNING':
      return '训练中'
    case 'COMPLETED':
      return '已完成'
    case 'FAILED':
      return '失败'
    case 'CANCELLED':
      return '已取消'
    default:
      return state.value.status
  }
})

const currentStageLabel = computed(() => {
  switch (state.value.currentStage) {
    case 'dataset_prepare':
      return '准备数据集'
    case 'training':
      return '训练'
    case 'completed':
      return '完成'
    case 'failed':
      return '失败'
    case 'cancelled':
      return '已取消'
    default:
      return ''
  }
})

const logText = computed(() => logLines.value.join('\n') || '暂无日志')

const progressStatus = computed(() => {
  if (state.value.status === 'FAILED') return 'exception'
  if (state.value.status === 'COMPLETED') return 'success'
  return ''
})

// 训练开始时自动切换到监控标签页
watch(
  () => state.value.status,
  (newStatus) => {
    if (newStatus === 'RUNNING' && activeTab.value === 'params') {
      activeTab.value = 'monitor'
    }
  }
)

async function fetchStatus() {
  try {
    const res = await gsApi.status(props.block.id)
    const d = res.data
    state.value.status = (d.gs_status as GSState['status']) ?? 'NOT_STARTED'
    state.value.progress = d.gs_progress ?? 0
    state.value.currentStage = d.gs_current_stage ?? null
    tensorboardUrl.value = d.tensorboard_url ?? null
  } catch {
    // ignore
  }
}

async function refreshStatus() {
  await fetchStatus()
}

async function fetchFiles() {
  try {
    const res = await gsApi.files(props.block.id)
    state.value.files = res.data.files
  } catch {
    // ignore
  }
}

async function fetchLog() {
  try {
    const res = await gsApi.logTail(props.block.id, 200)
    logLines.value = res.data.lines || []
  } catch {
    // ignore
  }
}

async function refreshAll() {
  await Promise.all([fetchStatus(), fetchFiles(), fetchLog()])
}

function startPolling() {
  if (!statusTimer) statusTimer = window.setInterval(fetchStatus, 2000)
  if (!logTimer) logTimer = window.setInterval(fetchLog, 2000)
}

function stopPolling() {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (logTimer) {
    clearInterval(logTimer)
    logTimer = null
  }
}

async function onStart() {
  try {
    loadingAction.value = true
    // Filter out undefined values to only send defined parameters
    const trainParams: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(params.value)) {
      // Skip undefined and null values
      if (value === undefined || value === null) {
        continue
      }
      // Skip empty arrays
      if (Array.isArray(value) && value.length === 0) {
        continue
      }
      trainParams[key] = value
    }
    await gsApi.train(props.block.id, {
      gpu_index: gpuIndex.value,
      train_params: trainParams as any,
    })
    await refreshAll()
    startPolling()
    ElMessage.success('已启动 3DGS 训练')
  } catch (e) {
    console.error(e)
    ElMessage.error('启动 3DGS 训练失败')
  } finally {
    loadingAction.value = false
  }
}

async function onCancel() {
  try {
    await ElMessageBox.confirm('确定要中止 3DGS 训练吗？', '提示', { type: 'warning' })
    loadingAction.value = true
    await gsApi.cancel(props.block.id)
    await refreshAll()
    stopPolling()
    ElMessage.success('已中止训练')
  } catch {
    // ignore
  } finally {
    loadingAction.value = false
  }
}

function toggleLog() {
  showLog.value = !showLog.value
}

async function refreshLog() {
  await fetchLog()
}

function formatSize(bytes: number): string {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let n = bytes
  let i = 0
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

// Visionary 内嵌预览（谨慎版，仅针对 SPZ） + 新标签页预览
const spzPreviewVisible = ref(false)
const spzPreviewUrl = ref<string | null>(null)
const spzPreviewFileName = ref<string | null>(null)
const cesiumPreviewVisible = ref(false)
const cesiumTilesetUrl = ref<string | null>(null)

// 下载相关状态
const downloadingFiles = ref<Record<string, boolean>>({})
const downloadingTilesFiles = ref<Record<string, boolean>>({})
const downloadProgress = ref<Record<string, number>>({})
const currentDownloadDialogVisible = ref(false)
const currentDownloadDialogTitle = ref('')
const currentDownloadProgress = ref(0)
const currentDownloadStatus = ref<'success' | 'exception' | undefined>(undefined)
const currentDownloadFileName = ref('')

// 3D Tiles 转换相关状态
const tilesStatus = ref<string>('NOT_STARTED')
const tilesProgress = ref(0)
const tilesCurrentStage = ref<string | null>(null)
const tilesError = ref<string | null>(null)
const tilesFiles = ref<Array<{
  name: string
  type: string
  size_bytes: number
  mtime: string
  preview_supported: boolean
  download_url: string
}>>([])
const loadingTilesStatus = ref(false)
const loadingTilesAction = ref(false)
const tilesConvertParams = ref({
  iteration: undefined as number | undefined,
  use_spz: false,
  optimize: false,
})

// 获取可用的迭代版本
const availableIterations = computed(() => {
  return state.value.files
    .filter(f => f.name.includes('iteration_') && f.name.endsWith('.ply'))
    .map(f => {
      const match = f.name.match(/iteration_(\d+)/)
      return match ? parseInt(match[1]) : null
    })
    .filter((v): v is number => v !== null)
    .sort((a, b) => b - a)
})

const tilesStatusTagType = computed(() => {
  switch (tilesStatus.value) {
    case 'COMPLETED':
      return 'success'
    case 'RUNNING':
      return 'primary'
    case 'FAILED':
      return 'danger'
    case 'CANCELLED':
      return 'warning'
    default:
      return 'info'
  }
})

const tilesStatusText = computed(() => {
  switch (tilesStatus.value) {
    case 'NOT_STARTED':
      return '未开始'
    case 'RUNNING':
      return '转换中'
    case 'COMPLETED':
      return '已完成'
    case 'FAILED':
      return '失败'
    case 'CANCELLED':
      return '已取消'
    default:
      return tilesStatus.value
  }
})

const tilesProgressStatus = computed(() => {
  if (tilesStatus.value === 'FAILED') return 'exception'
  if (tilesStatus.value === 'COMPLETED') return 'success'
  return ''
})

const canStartTilesConversion = computed(() => {
  return ['NOT_STARTED', 'FAILED', 'CANCELLED', 'COMPLETED'].includes(tilesStatus.value) &&
    state.value.status === 'COMPLETED'
})

// Get the latest previewable file (prefer .spz, then .ply)
const latestPreviewableFile = computed(() => {
  const previewableFiles = state.value.files.filter(f => f.preview_supported)
  if (previewableFiles.length === 0) return null
  
  // Prefer .spz files, then .ply files
  const spzFiles = previewableFiles.filter(f => f.name.endsWith('.spz'))
  if (spzFiles.length > 0) {
    // Return the latest SPZ file
    return spzFiles.sort((a, b) => new Date(b.mtime).getTime() - new Date(a.mtime).getTime())[0]
  }
  
  // Return the latest PLY file
  const plyFiles = previewableFiles.filter(f => f.name.endsWith('.ply'))
  if (plyFiles.length > 0) {
    return plyFiles.sort((a, b) => new Date(b.mtime).getTime() - new Date(a.mtime).getTime())[0]
  }
  
  // Fallback to any previewable file
  return previewableFiles.sort((a, b) => new Date(b.mtime).getTime() - new Date(a.mtime).getTime())[0]
})

// Latest SPZ file (Cautious: 内嵌预览只针对 SPZ，避免加载超级大的 PLY)
const latestSpzFile = computed<GSFileInfo | null>(() => {
  const spzFiles = state.value.files.filter(
    f => f.preview_supported && f.name.endsWith('.spz')
  )
  if (spzFiles.length === 0) return null
  return spzFiles.sort((a, b) => new Date(b.mtime).getTime() - new Date(a.mtime).getTime())[0]
})

const spzPreviewTitle = computed(() => {
  if (!spzPreviewFileName.value) return '3DGS 预览 (Visionary - SPZ)'
  const short = spzPreviewFileName.value.split('/').pop() || spzPreviewFileName.value
  return `3DGS 预览 (Visionary - SPZ) - ${short}`
})

function openSpzPreviewDialog(file?: GSFileInfo) {
  const target = file ?? latestSpzFile.value
  if (!target) {
    ElMessage.warning('没有可用于内嵌预览的 SPZ 文件')
    return
  }
  if (!target.name.endsWith('.spz')) {
    ElMessage.warning('内嵌预览目前仅支持 SPZ 文件')
    return
  }
  const absUrl = buildAbsoluteGsUrl(target.download_url)
  // 谨慎版本：内嵌预览直接复用 Simple Viewer（与“新标签页”相同的稳定代码路径）
  const base = getVisionarySimpleBaseUrl()
  spzPreviewUrl.value = `${base}?file_url=${encodeURIComponent(absUrl)}`
  spzPreviewFileName.value = target.name
  spzPreviewVisible.value = true
}

function buildAbsoluteGsUrl(downloadUrl: string): string {
  if (downloadUrl.startsWith('http://') || downloadUrl.startsWith('https://')) {
    return downloadUrl
  }
  if (downloadUrl.startsWith('/')) {
    return `${window.location.origin}${downloadUrl}`
  }
  // 相对路径的兜底处理
  const base = window.location.origin.replace(/\/$/, '')
  return `${base}/${downloadUrl.replace(/^\//, '')}`
}

function getVisionarySimpleBaseUrl(): string {
  // 允许通过环境变量注入自定义 Visionary Simple Viewer 地址
  // 例如 VITE_VISIONARY_SIMPLE_URL=http://localhost:3001/demo/simple/index.html
  // @ts-expect-error: Vite env 注入在运行时存在
  const envUrl = import.meta.env?.VITE_VISIONARY_SIMPLE_URL as string | undefined
  return envUrl || 'http://localhost:3001/demo/simple/index.html'
}

function openPreviewInNewTab(file: GSFileInfo) {
  const absFileUrl = buildAbsoluteGsUrl(file.download_url)
  const base = getVisionarySimpleBaseUrl()
  const url = `${base}?file_url=${encodeURIComponent(absFileUrl)}`
  window.open(url, '_blank', 'noopener,noreferrer')
}

function openLatestPreviewInNewTab() {
  if (!latestPreviewableFile.value) {
    ElMessage.warning('没有可预览的文件')
    return
  }
  openPreviewInNewTab(latestPreviewableFile.value)
}

async function openCesiumPreview(_file: { download_url: string }) {
  try {
    // Get tileset URL
    const response = await gsTilesApi.tilesetUrl(props.block.id)
    cesiumTilesetUrl.value = response.data.tileset_url
    cesiumPreviewVisible.value = true
  } catch (error: any) {
    ElMessage.error(`无法获取 tileset URL: ${error.message || '未知错误'}`)
  }
}

async function refreshTilesStatus() {
  if (loadingTilesStatus.value) return
  loadingTilesStatus.value = true
  try {
    const response = await gsTilesApi.status(props.block.id)
    const data = response.data
    tilesStatus.value = data.gs_tiles_status || 'NOT_STARTED'
    tilesProgress.value = data.gs_tiles_progress || 0
    tilesCurrentStage.value = data.gs_tiles_current_stage || null
    tilesError.value = data.gs_tiles_error_message || null

    // Refresh files if conversion is completed
    if (tilesStatus.value === 'COMPLETED') {
      await refreshTilesFiles()
    }
  } catch (error: any) {
    ElMessage.error(`刷新状态失败: ${error.message || '未知错误'}`)
  } finally {
    loadingTilesStatus.value = false
  }
}

async function refreshTilesFiles() {
  try {
    const response = await gsTilesApi.files(props.block.id)
    tilesFiles.value = response.data.files || []
  } catch (error: any) {
    console.error('Failed to refresh tiles files:', error)
  }
}

async function onStartTilesConversion() {
  if (loadingTilesAction.value) return
  loadingTilesAction.value = true
  try {
    await gsTilesApi.convert(props.block.id, {
      iteration: tilesConvertParams.value.iteration,
      use_spz: tilesConvertParams.value.use_spz,
      optimize: tilesConvertParams.value.optimize,
    })
    ElMessage.success('转换任务已启动')
    await refreshTilesStatus()
    // Start polling if conversion is running
    if (tilesStatus.value === 'RUNNING') {
      startTilesPolling()
    }
  } catch (error: any) {
    ElMessage.error(`启动转换失败: ${error.message || '未知错误'}`)
  } finally {
    loadingTilesAction.value = false
  }
}

async function onCancelTilesConversion() {
  if (loadingTilesAction.value) return
  loadingTilesAction.value = true
  try {
    await gsTilesApi.cancel(props.block.id)
    ElMessage.success('转换任务已取消')
    await refreshTilesStatus()
    stopTilesPolling()
  } catch (error: any) {
    ElMessage.error(`取消转换失败: ${error.message || '未知错误'}`)
  } finally {
    loadingTilesAction.value = false
  }
}

let tilesPollingTimer: number | null = null

function startTilesPolling() {
  if (tilesPollingTimer) return
  tilesPollingTimer = window.setInterval(async () => {
    await refreshTilesStatus()
    if (tilesStatus.value !== 'RUNNING') {
      stopTilesPolling()
    }
  }, 2000)
}

function stopTilesPolling() {
  if (tilesPollingTimer) {
    clearInterval(tilesPollingTimer)
    tilesPollingTimer = null
  }
}

function openTensorBoardFullscreen() {
  tensorboardFullscreenVisible.value = true
}

function openTensorBoardNewWindow() {
  if (tensorboardUrl.value) {
    window.open(tensorboardUrl.value, '_blank', 'noopener,noreferrer')
  }
}

// 下载文件函数
async function downloadFile(file: GSFileInfo) {
  const fileName = file.name
  if (downloadingFiles.value[fileName]) {
    return // 正在下载中，避免重复点击
  }

  // 对于超大文件（>1GB），使用直接下载方式，避免内存问题
  const fileSizeGB = file.size_bytes / (1024 * 1024 * 1024)
  const useDirectDownload = fileSizeGB > 1

  downloadingFiles.value[fileName] = true
  
  if (!useDirectDownload) {
    downloadProgress.value[fileName] = 0
    currentDownloadFileName.value = fileName
    currentDownloadDialogTitle.value = `下载 ${fileName.split('/').pop()}`
    currentDownloadProgress.value = 0
    currentDownloadStatus.value = undefined
    currentDownloadDialogVisible.value = true
  } else {
    ElMessage.info('文件较大，正在启动下载...')
  }

  try {
    // 构建完整的下载URL
    // 后端返回的 download_url 格式是 /api/blocks/...，直接使用相对路径即可
    // 浏览器会自动使用当前域名和端口（如 http://localhost:3000）
    // 注意：不要添加 apiBase，因为 download_url 已经包含了 /api 前缀
    const downloadUrl = file.download_url

    if (useDirectDownload) {
      // 对于大文件，直接使用浏览器下载
      const link = document.createElement('a')
      link.href = downloadUrl
      const actualFileName = fileName.split('/').pop() || fileName
      link.setAttribute('download', actualFileName)
      link.setAttribute('target', '_blank')
      document.body.appendChild(link)
      link.click()
      link.remove()
      ElMessage.success(`文件 ${actualFileName} 下载已开始`)
    } else {
      // 对于小文件，使用流式下载并显示进度
      const response = await fetch(downloadUrl)
      
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status} ${response.statusText}`)
      }

      const contentLength = response.headers.get('content-length')
      const total = contentLength ? parseInt(contentLength, 10) : 0

      // 创建ReadableStream来读取响应
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法读取响应流')
      }

      const chunks: Uint8Array[] = []
      let receivedLength = 0

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          break
        }

        chunks.push(value)
        receivedLength += value.length

        // 更新进度
        if (total > 0) {
          const progress = Math.round((receivedLength / total) * 100)
          downloadProgress.value[fileName] = progress
          if (currentDownloadFileName.value === fileName) {
            currentDownloadProgress.value = progress
          }
        }
      }

      // 创建Blob并触发下载
      const blob = new Blob(chunks as BlobPart[])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // 从文件路径中提取文件名
      const actualFileName = fileName.split('/').pop() || fileName
      link.setAttribute('download', actualFileName)
      
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      ElMessage.success(`文件 ${actualFileName} 下载成功`)
    }
  } catch (error: any) {
    console.error('下载失败:', error)
    ElMessage.error(`下载失败: ${error.message || '未知错误'}`)
    if (currentDownloadFileName.value === fileName) {
      currentDownloadStatus.value = 'exception'
    }
  } finally {
    downloadingFiles.value[fileName] = false
    // 延迟隐藏进度条，让用户看到100%
    if (!useDirectDownload) {
      if (currentDownloadFileName.value === fileName) {
        if (currentDownloadStatus.value !== 'exception') {
          currentDownloadProgress.value = 100
          currentDownloadStatus.value = 'success'
        }
        setTimeout(() => {
          currentDownloadDialogVisible.value = false
          downloadProgress.value[fileName] = 0
          currentDownloadFileName.value = ''
          currentDownloadStatus.value = undefined
        }, 1000)
      }
    }
  }
}

// 下载3D Tiles文件函数
async function downloadTilesFile(file: { name: string; download_url: string; size_bytes?: number }) {
  const fileName = file.name
  if (downloadingTilesFiles.value[fileName]) {
    return // 正在下载中，避免重复点击
  }

  // 对于超大文件（>1GB），使用直接下载方式，避免内存问题
  const fileSizeGB = (file.size_bytes || 0) / (1024 * 1024 * 1024)
  const useDirectDownload = fileSizeGB > 1

  downloadingTilesFiles.value[fileName] = true
  
  if (!useDirectDownload) {
    downloadProgress.value[fileName] = 0
    currentDownloadFileName.value = fileName
    currentDownloadDialogTitle.value = `下载 ${fileName}`
    currentDownloadProgress.value = 0
    currentDownloadStatus.value = undefined
    currentDownloadDialogVisible.value = true
  } else {
    ElMessage.info('文件较大，正在启动下载...')
  }

  try {
    // 构建完整的下载URL
    // 后端返回的 download_url 格式是 /api/blocks/...，直接使用相对路径即可
    // 浏览器会自动使用当前域名和端口（如 http://localhost:3000）
    // 注意：不要添加 apiBase，因为 download_url 已经包含了 /api 前缀
    const downloadUrl = file.download_url

    if (useDirectDownload) {
      // 对于大文件，直接使用浏览器下载
      const link = document.createElement('a')
      link.href = downloadUrl
      link.setAttribute('download', fileName)
      link.setAttribute('target', '_blank')
      document.body.appendChild(link)
      link.click()
      link.remove()
      ElMessage.success(`文件 ${fileName} 下载已开始`)
    } else {
      // 对于小文件，使用流式下载并显示进度
      const response = await fetch(downloadUrl)
      
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status} ${response.statusText}`)
      }

      const contentLength = response.headers.get('content-length')
      const total = contentLength ? parseInt(contentLength, 10) : 0

      // 创建ReadableStream来读取响应
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法读取响应流')
      }

      const chunks: Uint8Array[] = []
      let receivedLength = 0

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          break
        }

        chunks.push(value)
        receivedLength += value.length

        // 更新进度
        if (total > 0) {
          const progress = Math.round((receivedLength / total) * 100)
          downloadProgress.value[fileName] = progress
          if (currentDownloadFileName.value === fileName) {
            currentDownloadProgress.value = progress
          }
        }
      }

      // 创建Blob并触发下载
      const blob = new Blob(chunks as BlobPart[])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', fileName)
      
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      ElMessage.success(`文件 ${fileName} 下载成功`)
    }
  } catch (error: any) {
    console.error('下载失败:', error)
    ElMessage.error(`下载失败: ${error.message || '未知错误'}`)
    if (currentDownloadFileName.value === fileName) {
      currentDownloadStatus.value = 'exception'
    }
  } finally {
    downloadingTilesFiles.value[fileName] = false
    // 延迟隐藏进度条，让用户看到100%
    if (!useDirectDownload) {
      if (currentDownloadFileName.value === fileName) {
        if (currentDownloadStatus.value !== 'exception') {
          currentDownloadProgress.value = 100
          currentDownloadStatus.value = 'success'
        }
        setTimeout(() => {
          currentDownloadDialogVisible.value = false
          downloadProgress.value[fileName] = 0
          currentDownloadFileName.value = ''
          currentDownloadStatus.value = undefined
        }, 1000)
      }
    }
  }
}

onMounted(async () => {
  await refreshAll()
  if (state.value.status === 'RUNNING') startPolling()
  // Load tiles status if GS training is completed
  if (state.value.status === 'COMPLETED') {
    await refreshTilesStatus()
  }
})

onUnmounted(() => {
  stopPolling()
  stopTilesPolling()
})

watch(
  () => state.value.status,
  (s) => {
    if (s === 'RUNNING') startPolling()
    else stopPolling()
  },
)
</script>

<style scoped>
/* 顶部状态和快速操作区 */
.gs-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.status-section {
  flex: 1;
  min-width: 300px;
}

.status-line {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.status-label {
  font-weight: 600;
  color: #303133;
}

.stage-label {
  color: #909399;
  font-size: 13px;
  margin-left: 8px;
}

.status-progress {
  margin-top: 8px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 400px;
}

.quick-params {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.param-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.param-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* GPU资源卡片 */
.gpu-resource-card {
  margin-bottom: 16px;
  border: 2px solid var(--el-color-primary-light-8);
}

.gpu-resource-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 16px;
}

.gpu-resource-card :deep(.el-card__header .card-header) {
  color: white;
}

.card-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-icon {
  font-size: 18px;
}

/* 内容标签页 */
.gs-content-tabs {
  margin-top: 16px;
}

.gs-content-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.gs-content-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
}

/* 参数配置卡片 */
.params-card {
  margin-bottom: 16px;
}

.params-content {
  padding: 8px 0;
}

.params-section {
  margin-bottom: 16px;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-item label {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}


.advanced-params-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.param-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-row label {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.param-inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.param-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

/* 卡片通用样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.card-header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.files-card,
.log-card {
  margin-bottom: 16px;
}

.empty {
  padding: 12px 0;
}


.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-actions {
  display: flex;
  gap: 6px;
}

.log-text {
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.error-section {
  margin-top: 12px;
}

.error-box {
  background: #1f1f1f;
  color: #f5f5f5;
  padding: 10px;
  border-radius: 6px;
  overflow: auto;
}

.debug-section {
  margin-top: 12px;
}

.tiles-card {
  margin-bottom: 16px;
}

.tiles-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.tiles-status-section {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.tiles-actions-section {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.tiles-files-section {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.cesium-preview-wrap {
  width: 100%;
  height: 80vh;
  position: relative;
}

.cesium-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.preview-wrap {
  height: 75vh;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: 0;
}

/* TensorBoard 卡片样式 */
.tensorboard-card {
  margin-top: 12px;
}

.tensorboard-card :deep(.el-card__header) {
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: none;
}

.tensorboard-card :deep(.el-card__header .card-header) {
  color: white;
}

.tensorboard-card :deep(.el-card__header .el-button) {
  color: white;
}

.tensorboard-card :deep(.el-card__header .el-button:hover) {
  background-color: rgba(255, 255, 255, 0.1);
}

.card-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-icon {
  font-size: 18px;
}

.card-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.tensorboard-container {
  position: relative;
}

.tensorboard-preview {
  width: 100%;
  height: 600px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f7fa;
  position: relative;
}

.tensorboard-iframe {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}

.tensorboard-tips {
  margin-top: 12px;
}

.tensorboard-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 500px;
  background: #f5f7fa;
  border-radius: 6px;
  color: #909399;
}

/* TensorBoard 全屏对话框样式 */
.tensorboard-dialog :deep(.el-dialog__header) {
  padding: 16px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: none;
  margin: 0;
}

.tensorboard-dialog :deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
}

.tensorboard-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: white;
  font-size: 20px;
}

.tensorboard-dialog :deep(.el-dialog__headerbtn .el-dialog__close:hover) {
  color: rgba(255, 255, 255, 0.8);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.dialog-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
  color: white;
}

.dialog-icon {
  font-size: 20px;
}

.dialog-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.dialog-actions .el-button {
  color: white;
}

.dialog-actions .el-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.tensorboard-fullscreen-container {
  width: 100%;
  height: calc(95vh - 100px);
  min-height: 600px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f7fa;
}

.tensorboard-fullscreen-iframe {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .gs-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .quick-actions {
    min-width: 100%;
  }
  
  .tensorboard-preview {
    height: 400px;
  }
  
  .params-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .gs-header {
    padding: 12px;
  }
  
  .status-section {
    min-width: 100%;
  }
  
  .quick-params {
    flex-direction: column;
    align-items: stretch;
  }
  
  .param-group {
    width: 100%;
    justify-content: space-between;
  }
  
  .action-buttons {
    width: 100%;
    justify-content: stretch;
  }
  
  .action-buttons .el-button {
    flex: 1;
  }
  
  .tensorboard-preview {
    height: 300px;
  }
  
  .card-actions {
    flex-direction: column;
    gap: 4px;
  }
  
  .tensorboard-dialog {
    width: 98% !important;
    top: 1vh !important;
  }
  
  .tensorboard-fullscreen-container {
    height: calc(95vh - 80px);
  }
  
  .gs-content-tabs :deep(.el-tabs__item) {
    font-size: 12px;
    padding: 0 12px;
  }
}
</style>


