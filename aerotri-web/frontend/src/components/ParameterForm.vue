<template>
  <div class="parameter-form">
    <el-form :model="formData" label-width="160px" label-position="right">
      <!-- Algorithm Selection -->
      <el-divider content-position="left">基本设置</el-divider>
      
      <el-form-item label="重建算法">
        <el-radio-group v-model="formData.algorithm">
          <el-radio value="glomap">GLOMAP (全局式)</el-radio>
          <el-radio value="colmap">COLMAP (增量式)</el-radio>
          <el-radio value="instantsfm">InstantSfM (快速全局式)</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="匹配方法">
        <el-select v-model="formData.matching_method" style="width: 100%">
          <el-option label="序列匹配 (Sequential)" value="sequential" />
          <el-option label="穷举匹配 (Exhaustive)" value="exhaustive" />
          <el-option label="词汇树匹配 (Vocab Tree)" value="vocab_tree" />
          <el-option label="空间匹配 (Spatial)" value="spatial" />
        </el-select>
      </el-form-item>

      <!-- Feature Extraction -->
      <el-divider content-position="left">特征提取</el-divider>

      <el-form-item label="GPU 加速">
        <el-switch v-model="formData.feature_params.use_gpu" />
      </el-form-item>

      <el-form-item label="相机模型">
        <el-select v-model="formData.feature_params.camera_model" style="width: 100%">
          <el-option label="SIMPLE_RADIAL" value="SIMPLE_RADIAL" />
          <el-option label="PINHOLE" value="PINHOLE" />
          <el-option label="SIMPLE_PINHOLE" value="SIMPLE_PINHOLE" />
          <el-option label="RADIAL" value="RADIAL" />
          <el-option label="OPENCV" value="OPENCV" />
        </el-select>
      </el-form-item>

      <el-form-item label="单相机模式">
        <el-switch v-model="formData.feature_params.single_camera" />
        <el-text type="info" size="small" style="margin-left: 8px">
          所有图像使用相同相机参数
        </el-text>
      </el-form-item>

      <el-form-item label="最大图像尺寸">
        <el-input-number
          v-model="formData.feature_params.max_image_size"
          :min="500"
          :max="8000"
          :step="100"
        />
        <el-text type="info" size="small" style="margin-left: 8px">
          像素
        </el-text>
      </el-form-item>

      <el-form-item label="最大特征数">
        <el-input-number
          v-model="formData.feature_params.max_num_features"
          :min="1000"
          :max="50000"
          :step="1000"
        />
      </el-form-item>

      <!-- Matching Parameters -->
      <el-divider content-position="left">特征匹配</el-divider>

      <el-form-item label="匹配 GPU 加速">
        <el-switch v-model="formData.matching_params.use_gpu" />
      </el-form-item>

      <el-form-item label="序列重叠" v-if="formData.matching_method === 'sequential'">
        <el-input-number
          v-model="formData.matching_params.overlap"
          :min="5"
          :max="100"
          :step="5"
        />
        <el-text type="info" size="small" style="margin-left: 8px">
          窗口大小
        </el-text>
      </el-form-item>

      <!-- Vocab Tree parameters -->
      <el-form-item
        label="词汇树路径"
        v-if="formData.matching_method === 'vocab_tree'"
      >
        <el-input
          v-model="formData.matching_params.vocab_tree_path"
          placeholder="例如：/path/to/vocab_tree.bin，留空则使用服务器默认配置（如有）"
          clearable
        />
      </el-form-item>

      <!-- Spatial matching parameters -->
      <template v-if="formData.matching_method === 'spatial'">
        <el-form-item label="最大邻居数">
          <el-input-number
            v-model="formData.matching_params.spatial_max_num_neighbors"
            :min="1"
            :max="200"
            :step="1"
          />
          <el-text type="info" size="small" style="margin-left: 8px">
            每张影像匹配的空间最近邻影像数量
          </el-text>
        </el-form-item>

        <el-form-item label="忽略高度 (Z)">
          <el-switch v-model="formData.matching_params.spatial_ignore_z" />
          <el-text type="info" size="small" style="margin-left: 8px">
            对只有平面精度的航测数据，可忽略高度分量，只按平面距离匹配
          </el-text>
        </el-form-item>
        <el-text type="info" size="small" style="display: block; margin-top: -8px; margin-bottom: 16px; color: var(--el-text-color-secondary)">
          注意：COLMAP 会自动从数据库检测坐标类型（GPS 或笛卡尔坐标），无需手动指定
        </el-text>
      </template>

      <!-- Mapper Parameters -->
      <el-divider content-position="left">Mapper 参数</el-divider>

      <template v-if="formData.algorithm === 'colmap'">
        <el-form-item label="使用 Pose Prior">
          <el-switch v-model="(formData.mapper_params as any).use_pose_prior" />
          <el-text type="info" size="small" style="margin-left: 8px">
            使用图像 EXIF GPS（lat/lon/alt）位置先验加速重建
          </el-text>
        </el-form-item>

        <el-form-item label="BA GPU 加速">
          <el-switch v-model="formData.mapper_params.ba_use_gpu" />
        </el-form-item>
      </template>

      <template v-else-if="formData.algorithm === 'glomap'">
        <el-form-item label="使用 Pose Prior">
          <el-switch v-model="(formData.mapper_params as any).use_pose_prior" />
          <el-text type="info" size="small" style="margin-left: 8px">
            使用图像 EXIF GPS（lat/lon/alt）位置先验加速 GP/BA
          </el-text>
        </el-form-item>

        <el-form-item label="GlobalPositioning GPU">
          <el-switch v-model="formData.mapper_params.global_positioning_use_gpu" />
        </el-form-item>

        <el-form-item label="BundleAdjustment GPU">
          <el-switch v-model="formData.mapper_params.bundle_adjustment_use_gpu" />
        </el-form-item>

        <el-collapse v-model="glomapActiveNames" style="margin-top: 16px">
          <!-- 跳过阶段 -->
          <el-collapse-item name="skip_stages" title="跳过阶段（Skip Stages）">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        >
          这些参数控制 GLOMAP mapper 是否跳过某些处理阶段。对于 mapper_resume 模式，部分阶段会被强制跳过。
        </el-alert>

        <el-form-item label="跳过预处理">
          <el-switch v-model="(formData.mapper_params as any).skip_preprocessing" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过特征提取和匹配的预处理阶段
          </el-text>
        </el-form-item>

        <el-form-item label="跳过视图图校准">
          <el-switch v-model="(formData.mapper_params as any).skip_view_graph_calibration" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过视图图校准阶段
          </el-text>
        </el-form-item>

        <el-form-item label="跳过相对位姿估计">
          <el-switch v-model="(formData.mapper_params as any).skip_relative_pose_estimation" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过相对位姿估计阶段
          </el-text>
        </el-form-item>

        <el-form-item label="跳过旋转平均">
          <el-switch v-model="(formData.mapper_params as any).skip_rotation_averaging" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过全局旋转平均阶段
          </el-text>
        </el-form-item>

        <el-form-item label="跳过轨迹建立">
          <el-switch v-model="(formData.mapper_params as any).skip_track_establishment" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过特征轨迹建立阶段
          </el-text>
        </el-form-item>

        <el-form-item label="跳过全局定位">
          <el-switch v-model="(formData.mapper_params as any).skip_global_positioning" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过全局位置估计阶段（mapper_resume 模式可用）
          </el-text>
        </el-form-item>

        <el-form-item label="跳过束调整">
          <el-switch v-model="(formData.mapper_params as any).skip_bundle_adjustment" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过 Bundle Adjustment 优化阶段（mapper_resume 模式可用）
          </el-text>
        </el-form-item>

        <el-form-item label="跳过重三角化">
          <el-switch v-model="(formData.mapper_params as any).skip_retriangulation" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过重三角化阶段
          </el-text>
        </el-form-item>

        <el-form-item label="跳过剪枝">
          <el-switch v-model="(formData.mapper_params as any).skip_pruning" />
          <el-text type="info" size="small" style="margin-left: 8px">
            跳过结果剪枝阶段（mapper_resume 模式可用，默认 true）
          </el-text>
        </el-form-item>
          </el-collapse-item>

          <!-- 迭代参数 -->
          <el-collapse-item name="iteration_params" title="迭代参数（Iteration Parameters）">
            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">ba_iteration_num</div>
                </div>
              </template>
              <div class="param-control">
          <el-input-number
            v-model="(formData.mapper_params as any).ba_iteration_num"
            :min="1"
            :max="10"
            :step="1"
            :placeholder="3"
          />
                <el-text type="info" size="small" class="param-desc">
            Bundle Adjustment 迭代次数（留空使用默认值：3）
          </el-text>
              </div>
        </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">retriangulation_iteration_num</div>
                </div>
              </template>
              <div class="param-control">
          <el-input-number
            v-model="(formData.mapper_params as any).retriangulation_iteration_num"
            :min="1"
            :max="10"
            :step="1"
            :placeholder="1"
          />
                <el-text type="info" size="small" class="param-desc">
            重三角化迭代次数（留空使用默认值：1）
          </el-text>
              </div>
            </el-form-item>
          </el-collapse-item>

          <!-- 轨迹建立 -->
          <el-collapse-item name="track_establishment" title="轨迹建立（Track Establishment）">
            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">TrackEstablishment.min_num_tracks_per_view</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).track_establishment_min_num_tracks_per_view"
                  :min="-1"
                  :max="10000"
                  :step="1"
                  :placeholder="-1"
                />
                <el-text type="info" size="small" class="param-desc">
                  每个视图的最小轨迹数（-1 表示不限制）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">TrackEstablishment.min_num_view_per_track</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).track_establishment_min_num_view_per_track"
                  :min="2"
                  :max="100"
                  :step="1"
                  :placeholder="3"
                />
                <el-text type="info" size="small" class="param-desc">
                  每个轨迹的最小视图数（默认：3）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">TrackEstablishment.max_num_view_per_track</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).track_establishment_max_num_view_per_track"
                  :min="2"
                  :max="1000"
                  :step="10"
                  :placeholder="100"
                />
                <el-text type="info" size="small" class="param-desc">
                  每个轨迹的最大视图数（默认：100）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">TrackEstablishment.max_num_tracks</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).track_establishment_max_num_tracks"
                  :min="1000"
                  :max="100000000"
                  :step="1000000"
                  :placeholder="10000000"
                />
                <el-text type="info" size="small" class="param-desc">
                  最大轨迹数（默认：10000000）
                </el-text>
              </div>
            </el-form-item>
          </el-collapse-item>

          <!-- 全局定位 -->
          <el-collapse-item name="global_positioning" title="全局定位（Global Positioning）">
            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">GlobalPositioning.optimize_positions</div>
                </div>
              </template>
              <div class="param-control">
                <el-switch v-model="(formData.mapper_params as any).global_positioning_optimize_positions" />
                <el-text type="info" size="small" class="param-desc">
                  是否优化相机位置（默认：true）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">GlobalPositioning.optimize_points</div>
                </div>
              </template>
              <div class="param-control">
                <el-switch v-model="(formData.mapper_params as any).global_positioning_optimize_points" />
                <el-text type="info" size="small" class="param-desc">
                  是否优化3D点（默认：true）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">GlobalPositioning.optimize_scales</div>
                </div>
              </template>
              <div class="param-control">
                <el-switch v-model="(formData.mapper_params as any).global_positioning_optimize_scales" />
                <el-text type="info" size="small" class="param-desc">
                  是否优化尺度（默认：true）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">GlobalPositioning.thres_loss_function</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).global_positioning_thres_loss_function"
                  :min="1e-3"
                  :max="10"
                  :step="0.1"
                  :precision="3"
                  :placeholder="0.1"
                />
                <el-text type="info" size="small" class="param-desc">
                  Huber 损失函数阈值（默认：0.1）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">GlobalPositioning.max_num_iterations</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).global_positioning_max_num_iterations"
                  :min="10"
                  :max="1000"
                  :step="10"
                  :placeholder="100"
                />
                <el-text type="info" size="small" class="param-desc">
                  优化器最大迭代次数（默认：100）
                </el-text>
              </div>
            </el-form-item>
          </el-collapse-item>

          <!-- 束调整 -->
          <el-collapse-item name="bundle_adjustment" title="束调整（Bundle Adjustment）">
            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">BundleAdjustment.optimize_rotations</div>
                </div>
              </template>
              <div class="param-control">
                <el-switch v-model="(formData.mapper_params as any).bundle_adjustment_optimize_rotations" />
                <el-text type="info" size="small" class="param-desc">
                  是否优化相机旋转（默认：true）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">BundleAdjustment.optimize_translation</div>
                </div>
              </template>
              <div class="param-control">
                <el-switch v-model="(formData.mapper_params as any).bundle_adjustment_optimize_translation" />
                <el-text type="info" size="small" class="param-desc">
                  是否优化相机平移（默认：true）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">BundleAdjustment.optimize_intrinsics</div>
                </div>
              </template>
              <div class="param-control">
                <el-switch v-model="(formData.mapper_params as any).bundle_adjustment_optimize_intrinsics" />
                <el-text type="info" size="small" class="param-desc">
                  是否优化相机内参（默认：true）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">BundleAdjustment.optimize_principal_point</div>
                </div>
              </template>
              <div class="param-control">
                <el-switch v-model="(formData.mapper_params as any).bundle_adjustment_optimize_principal_point" />
                <el-text type="info" size="small" class="param-desc">
                  是否优化主点（默认：false）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">BundleAdjustment.optimize_points</div>
                </div>
              </template>
              <div class="param-control">
                <el-switch v-model="(formData.mapper_params as any).bundle_adjustment_optimize_points" />
                <el-text type="info" size="small" class="param-desc">
                  是否优化3D点（默认：true）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">BundleAdjustment.thres_loss_function</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).bundle_adjustment_thres_loss_function"
                  :min="0.1"
                  :max="10"
                  :step="0.1"
                  :precision="1"
                  :placeholder="1.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  Huber 损失函数阈值（默认：1.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">BundleAdjustment.max_num_iterations</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).bundle_adjustment_max_num_iterations"
                  :min="50"
                  :max="1000"
                  :step="50"
                  :placeholder="200"
                />
                <el-text type="info" size="small" class="param-desc">
                  优化器最大迭代次数（默认：200）
                </el-text>
              </div>
            </el-form-item>
          </el-collapse-item>

          <!-- 重三角化 -->
          <el-collapse-item name="triangulation" title="重三角化（Retriangulation）">
            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Triangulation.complete_max_reproj_error</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).triangulation_complete_max_reproj_error"
                  :min="1"
                  :max="50"
                  :step="1"
                  :precision="1"
                  :placeholder="15.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  完成三角化的最大重投影误差（像素，默认：15.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Triangulation.merge_max_reproj_error</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).triangulation_merge_max_reproj_error"
                  :min="1"
                  :max="50"
                  :step="1"
                  :precision="1"
                  :placeholder="15.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  合并轨迹的最大重投影误差（像素，默认：15.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Triangulation.min_angle</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).triangulation_min_angle"
                  :min="0.1"
                  :max="10"
                  :step="0.1"
                  :precision="1"
                  :placeholder="1.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  最小三角化角度（度，默认：1.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Triangulation.min_num_matches</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).triangulation_min_num_matches"
                  :min="5"
                  :max="100"
                  :step="1"
                  :placeholder="15"
                />
                <el-text type="info" size="small" class="param-desc">
                  三角化所需的最小匹配数（默认：15）
                </el-text>
              </div>
            </el-form-item>
          </el-collapse-item>

          <!-- 内点阈值 -->
          <el-collapse-item name="thresholds" title="内点阈值（Inlier Thresholds）">
            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.max_angle_error</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_max_angle_error"
                  :min="0.1"
                  :max="10"
                  :step="0.1"
                  :precision="1"
                  :placeholder="1.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  全局定位的最大角度误差（度，默认：1.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.max_reprojection_error</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_max_reprojection_error"
                  :min="1e-3"
                  :max="1"
                  :step="1e-3"
                  :precision="3"
                  :placeholder="0.01"
                />
                <el-text type="info" size="small" class="param-desc">
                  束调整的最大重投影误差（默认：0.01）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.min_triangulation_angle</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_min_triangulation_angle"
                  :min="0.1"
                  :max="10"
                  :step="0.1"
                  :precision="1"
                  :placeholder="1.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  三角化的最小角度（度，默认：1.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.max_epipolar_error_E</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_max_epipolar_error_E"
                  :min="0.1"
                  :max="10"
                  :step="0.1"
                  :precision="1"
                  :placeholder="1.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  本质矩阵的最大对极误差（默认：1.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.max_epipolar_error_F</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_max_epipolar_error_F"
                  :min="0.1"
                  :max="20"
                  :step="0.1"
                  :precision="1"
                  :placeholder="4.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  基础矩阵的最大对极误差（默认：4.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.max_epipolar_error_H</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_max_epipolar_error_H"
                  :min="0.1"
                  :max="20"
                  :step="0.1"
                  :precision="1"
                  :placeholder="4.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  单应矩阵的最大对极误差（默认：4.0）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.min_inlier_num</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_min_inlier_num"
                  :min="5"
                  :max="500"
                  :step="5"
                  :placeholder="30"
                />
                <el-text type="info" size="small" class="param-desc">
                  图像对的最小内点数（默认：30）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.min_inlier_ratio</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_min_inlier_ratio"
                  :min="0.01"
                  :max="1"
                  :step="0.01"
                  :precision="2"
                  :placeholder="0.25"
                />
                <el-text type="info" size="small" class="param-desc">
                  图像对的最小内点比例（默认：0.25）
                </el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="param-label">
                  <div class="param-name">Thresholds.max_rotation_error</div>
                </div>
              </template>
              <div class="param-control">
                <el-input-number
                  v-model="(formData.mapper_params as any).thresholds_max_rotation_error"
                  :min="0.1"
                  :max="90"
                  :step="0.1"
                  :precision="1"
                  :placeholder="10.0"
                />
                <el-text type="info" size="small" class="param-desc">
                  旋转平均的最大旋转误差（度，默认：10.0）
                </el-text>
              </div>
        </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </template>

      <template v-else-if="formData.algorithm === 'instantsfm'">
        <!-- InstantSfM Basic Parameters -->
        <el-divider content-position="left">InstantSfM 基本参数</el-divider>
        
        <el-form-item label="启用实时可视化">
          <el-switch v-model="(formData.mapper_params as InstantsfmMapperParams).enable_visualization" />
          <el-text type="info" size="small" style="margin-left: 8px">
            实时显示优化过程、相机位姿和点云（需要 InstantSfM 支持）
          </el-text>
        </el-form-item>
        
        <el-form-item 
          label="可视化端口" 
          v-if="(formData.mapper_params as InstantsfmMapperParams).enable_visualization"
        >
          <el-input-number
            v-model="(formData.mapper_params as InstantsfmMapperParams).visualization_port"
            :min="1024"
            :max="65535"
            :step="1"
            :placeholder="8080"
            clearable
          />
          <el-text type="info" size="small" style="margin-left: 8px">
            留空则自动检测 viser 服务器端口
          </el-text>
        </el-form-item>
        <el-form-item label="导出文本格式">
          <el-switch v-model="formData.mapper_params.export_txt" />
          <el-text type="info" size="small" style="margin-left: 8px">
            导出 cameras.txt, images.txt, points3D.txt
          </el-text>
        </el-form-item>

        <el-form-item label="禁用深度信息">
          <el-switch v-model="formData.mapper_params.disable_depths" />
        </el-form-item>

        <el-form-item label="自定义配置文件名">
          <el-input
            v-model="formData.mapper_params.manual_config_name"
            placeholder="留空使用默认配置 (colmap)"
            clearable
          />
        </el-form-item>

        <el-form-item label="GPU 索引">
          <el-input-number
            v-model="formData.mapper_params.gpu_index"
            :min="0"
            :max="15"
            :step="1"
          />
          <el-text type="info" size="small" style="margin-left: 8px">
            指定使用的 GPU 设备编号（0-15）
          </el-text>
        </el-form-item>

        <el-form-item label="束调整迭代次数">
          <el-input-number
            v-model="formData.mapper_params.num_iteration_bundle_adjustment"
            :min="1"
            :max="10"
          />
        </el-form-item>

        <el-form-item label="束调整最大迭代次数">
          <el-input-number
            v-model="formData.mapper_params.bundle_adjustment_max_iterations"
            :min="50"
            :max="500"
            :step="50"
          />
        </el-form-item>

        <el-form-item label="束调整函数容差">
          <el-input-number
            v-model="formData.mapper_params.bundle_adjustment_function_tolerance"
            :min="1e-6"
            :max="1e-2"
            :step="1e-4"
            :precision="6"
          />
        </el-form-item>

        <el-form-item label="全局定位最大迭代次数">
          <el-input-number
            v-model="formData.mapper_params.global_positioning_max_iterations"
            :min="50"
            :max="200"
            :step="10"
          />
        </el-form-item>

        <el-form-item label="全局定位函数容差">
          <el-input-number
            v-model="formData.mapper_params.global_positioning_function_tolerance"
            :min="1e-6"
            :max="1e-2"
            :step="1e-4"
            :precision="6"
          />
        </el-form-item>

        <el-form-item label="最小匹配数">
          <el-input-number
            v-model="formData.mapper_params.min_num_matches"
            :min="10"
            :max="100"
            :step="5"
          />
        </el-form-item>

        <el-form-item label="最小三角化角度">
          <el-input-number
            v-model="formData.mapper_params.min_triangulation_angle"
            :min="0.5"
            :max="5.0"
            :step="0.5"
            :precision="1"
          />
          <el-text type="info" size="small" style="margin-left: 8px">
            度
          </el-text>
        </el-form-item>
      </template>
    </el-form>

    <div class="form-actions">
      <el-button @click="$emit('cancel')">取消</el-button>
      <el-button type="primary" @click="handleSave">保存</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { Block, FeatureParams, MatchingParams, GlomapMapperParams, ColmapMapperParams, InstantsfmMapperParams } from '@/types'

const props = defineProps<{
  block: Block
}>()

const emit = defineEmits<{
  (e: 'save', params: Partial<Block>): void
  (e: 'cancel'): void
}>()

// Collapse panel active names for GLOMAP parameters (default: all collapsed)
const glomapActiveNames = ref<string[]>([])

// Default parameters
const defaultFeatureParams: FeatureParams = {
  use_gpu: true,
  gpu_index: 0,
  max_image_size: 2640,
  max_num_features: 20000,
  camera_model: 'OPENCV',
  single_camera: true,
}

const defaultMatchingParams: MatchingParams = {
  method: 'sequential',
  overlap: 10,
  use_gpu: true,
  gpu_index: 0,
  vocab_tree_path: undefined,
  spatial_max_num_neighbors: 50,
  spatial_ignore_z: false,
}

const defaultGlomapParams: GlomapMapperParams = {
  use_pose_prior: false,
  global_positioning_use_gpu: true,
  global_positioning_gpu_index: 0,
  bundle_adjustment_use_gpu: true,
  bundle_adjustment_gpu_index: 0,
  // Skip stage flags (defaults match GLOMAP option_manager.cc)
  skip_preprocessing: false,
  skip_view_graph_calibration: false,
  skip_relative_pose_estimation: false,
  skip_rotation_averaging: false,
  skip_track_establishment: false,
  skip_global_positioning: false,
  skip_bundle_adjustment: false,
  skip_retriangulation: false,
  skip_pruning: true,
  // Iteration parameters
  ba_iteration_num: undefined,
  retriangulation_iteration_num: undefined,
  // Track Establishment parameters (defaults from track_establishment.h)
  track_establishment_min_num_tracks_per_view: undefined, // -1 (use undefined to let GLOMAP use default)
  track_establishment_min_num_view_per_track: undefined, // 3
  track_establishment_max_num_view_per_track: undefined, // 100
  track_establishment_max_num_tracks: undefined, // 10000000
  // Global Positioning parameters (defaults from global_positioning.h)
  // For boolean params with default=true, set to true so switch shows correct state
  global_positioning_optimize_positions: true, // GLOMAP default: true
  global_positioning_optimize_points: true, // GLOMAP default: true
  global_positioning_optimize_scales: true, // GLOMAP default: true
  global_positioning_thres_loss_function: undefined, // 0.1
  global_positioning_max_num_iterations: undefined, // 100
  // Bundle Adjustment parameters (defaults from bundle_adjustment.h)
  // For boolean params with default=true, set to true so switch shows correct state
  bundle_adjustment_optimize_rotations: true, // GLOMAP default: true
  bundle_adjustment_optimize_translation: true, // GLOMAP default: true
  bundle_adjustment_optimize_intrinsics: true, // GLOMAP default: true
  bundle_adjustment_optimize_principal_point: false, // GLOMAP default: false
  bundle_adjustment_optimize_points: true, // GLOMAP default: true
  bundle_adjustment_thres_loss_function: undefined, // 1.0
  bundle_adjustment_max_num_iterations: undefined, // 200
  // Triangulation parameters (defaults from track_retriangulation.h)
  triangulation_complete_max_reproj_error: undefined, // 15.0
  triangulation_merge_max_reproj_error: undefined, // 15.0
  triangulation_min_angle: undefined, // 1.0
  triangulation_min_num_matches: undefined, // 15
  // Inlier Thresholds parameters (defaults from types.h)
  thresholds_max_angle_error: undefined, // 1.0
  thresholds_max_reprojection_error: undefined, // 0.01
  thresholds_min_triangulation_angle: undefined, // 1.0
  thresholds_max_epipolar_error_E: undefined, // 1.0
  thresholds_max_epipolar_error_F: undefined, // 4.0
  thresholds_max_epipolar_error_H: undefined, // 4.0
  thresholds_min_inlier_num: undefined, // 30
  thresholds_min_inlier_ratio: undefined, // 0.25
  thresholds_max_rotation_error: undefined, // 10.0
}

const defaultColmapParams: ColmapMapperParams = {
  use_pose_prior: false,
  ba_use_gpu: true,
  ba_gpu_index: 0,
}

const defaultInstantsfmParams: InstantsfmMapperParams = {
  export_txt: true,
  disable_depths: false,
  manual_config_name: null,
  gpu_index: 0,
  num_iteration_bundle_adjustment: 3,
  bundle_adjustment_max_iterations: 200,
  bundle_adjustment_function_tolerance: 5e-4,
  global_positioning_max_iterations: 100,
  global_positioning_function_tolerance: 5e-4,
  min_num_matches: 30,
  min_triangulation_angle: 1.5,
  enable_visualization: false,
  visualization_port: null,
}

const formData = reactive({
  algorithm: props.block.algorithm,
  matching_method: props.block.matching_method,
  feature_params: { ...defaultFeatureParams, ...props.block.feature_params },
  matching_params: { ...defaultMatchingParams, ...props.block.matching_params },
  mapper_params: props.block.algorithm === 'glomap'
    ? { ...defaultGlomapParams, ...(props.block.mapper_params as GlomapMapperParams) }
    : props.block.algorithm === 'instantsfm'
    ? { ...defaultInstantsfmParams, ...(props.block.mapper_params as InstantsfmMapperParams) }
    : { ...defaultColmapParams, ...(props.block.mapper_params as ColmapMapperParams) },
})

// Watch algorithm changes to update mapper params
watch(() => formData.algorithm, (algorithm) => {
  if (algorithm === 'glomap') {
    formData.mapper_params = { ...defaultGlomapParams }
  } else if (algorithm === 'instantsfm') {
    formData.mapper_params = { ...defaultInstantsfmParams }
  } else {
    formData.mapper_params = { ...defaultColmapParams }
  }
})

// Keep matching_params.method consistent with matching_method selection
watch(() => formData.matching_method, (method) => {
  formData.matching_params.method = method
}, { immediate: true })

function handleSave() {
  emit('save', {
    algorithm: formData.algorithm,
    matching_method: formData.matching_method,
    feature_params: formData.feature_params,
    matching_params: formData.matching_params,
    mapper_params: formData.mapper_params,
  })
}
</script>

<style scoped>
.parameter-form {
  padding: 0 20px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

/* 参数标签样式 - 英文参数名显示 */
.param-label {
  width: 100%;
  min-width: 280px;
  padding-right: 16px;
}

.param-name {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
  word-break: break-all;
  user-select: text;
}

/* 参数控制区域样式 */
.param-control {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.param-desc {
  flex-shrink: 0;
  white-space: nowrap;
  color: #909399;
}

/* 针对 GLOMAP 参数区域的特殊样式 */
.glomap-params-collapse :deep(.el-collapse-item__content) {
  padding: 16px 0;
}

.glomap-params-collapse :deep(.el-collapse-item__content .el-form-item) {
  margin-bottom: 20px;
}

.glomap-params-collapse :deep(.el-collapse-item__content .el-form-item__label) {
  width: auto !important;
  min-width: 300px;
  max-width: 350px;
  padding-right: 16px;
  line-height: 1.5;
  text-align: left;
  vertical-align: top;
  padding-top: 0;
}

.glomap-params-collapse :deep(.el-collapse-item__content .el-form-item__content) {
  flex: 1;
  min-width: 0;
  margin-left: 0 !important;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .param-label {
    min-width: 240px;
  }
  
  .glomap-params-collapse :deep(.el-collapse-item__content .el-form-item__label) {
    min-width: 240px;
    max-width: 280px;
  }
  
  .param-control {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .param-desc {
    white-space: normal;
  }
}
</style>
