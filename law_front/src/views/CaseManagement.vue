<template>
  <div class="case-management">
    <div class="page-header">
      <h2>案件文档管理</h2>
      <div class="header-actions">
        <div class="search-box">
          <input type="text" v-model="searchQuery" placeholder="搜索文档..." />
        </div>
        <div class="filter-box">
          <select v-model="filterCategory" @change="loadFiles">
            <option value="">全部分类</option>
            <option value="case">案件文档</option>
            <option value="contract">合同文档</option>
            <option value="template">模板文档</option>
            <option value="general">普通文档</option>
          </select>
        </div>
        <div v-if="selectedFileIds.length > 0" class="batch-actions">
          <span class="selected-count">已选择 {{ selectedFileIds.length }} 个文件</span>
          <button class="batch-btn upload-btn" @click="showBatchKnowledgeUploadDialog">
            批量上传知识库
          </button>
          <button class="batch-btn delete-btn" @click="showBatchDeleteConfirmDialog">
            批量删除
          </button>
        </div>
        <button class="add-button" @click="showUploadDialog">
          <span class="add-icon">+</span> 上传文档
        </button>
      </div>
    </div>

    <!-- 文档表格 -->
    <div class="file-table">
      <table>
        <thead>
          <tr>
            <th class="checkbox-column">
              <input type="checkbox" 
                     :checked="isAllSelected" 
                     @change="toggleSelectAll"
                     :indeterminate="isIndeterminate">
            </th>
            <th>文件名</th>
            <th>文件分类</th>
            <th>案件主题</th>
            <th>备注</th>
            <th>知识库状态</th>
            <th>上传时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="file in filteredFiles" :key="file.id">
            <td class="checkbox-column">
              <input type="checkbox" 
                     :value="file.id" 
                     v-model="selectedFileIds">
            </td>
            <td>{{ file.filename }}</td>
            <td @dblclick="startEdit(file, 'file_category')" class="editable-cell">
              <div v-if="editingFile === file.id && editingField === 'file_category'" class="edit-mode">
                <select v-model="editForm.file_category" 
                        @blur="saveEdit(file)" 
                        @change="saveEdit(file)"
                        @keyup.esc="cancelEdit()"
                        class="edit-select">
                  <option value="case">案件文档</option>
                  <option value="contract">合同文档</option>
                  <option value="template">模板文档</option>
                  <option value="general">普通文档</option>
                </select>
              </div>
              <div v-else class="view-mode">
                <span class="category-tag" :class="file.file_category">
                  {{ getCategoryName(file.file_category) }}
                </span>
              </div>
            </td>
            <td @dblclick="startEdit(file, 'case_title')" class="editable-cell">
              <div v-if="editingFile === file.id && editingField === 'case_title'" class="edit-mode">
                <input v-model="editForm.case_title" 
                       @blur="saveEdit(file)" 
                       @keyup.enter="saveEdit(file)"
                       @keyup.esc="cancelEdit()"
                       class="edit-input"
                       placeholder="请输入案件主题"
                       ref="editInput" />
              </div>
              <div v-else class="view-mode">
                {{ file.case_title || '-' }}
              </div>
            </td>
            <td @dblclick="startEdit(file, 'case_summary')" class="summary-cell editable-cell">
              <div v-if="editingFile === file.id && editingField === 'case_summary'" class="edit-mode">
                <textarea v-model="editForm.case_summary" 
                          @blur="saveEdit(file)" 
                          @keyup.enter="saveEdit(file)"
                          @keyup.esc="cancelEdit()"
                          class="edit-textarea"
                          placeholder="请输入备注"
                          rows="2"></textarea>
              </div>
              <div v-else class="view-mode">
                {{ file.case_summary || '-' }}
              </div>
            </td>
            <td class="knowledge-status">
              <div class="status-tags">
                <div class="status-item">
                  <span class="status-tag" :class="getKnowledgeStatus(file, 'public')">
                    {{ getKnowledgeStatusText(file, 'public') }}
                  </span>
                  <button v-if="file.public_knowledge_uploaded" 
                          class="cancel-upload-btn" 
                          @click="showCancelUploadDialog(file, 'public')"
                          title="撤销公有知识库上传">
                    ×
                  </button>
                </div>
                <div class="status-item">
                  <span class="status-tag" :class="getKnowledgeStatus(file, 'private')">
                    {{ getKnowledgeStatusText(file, 'private') }}
                  </span>
                  <button v-if="file.private_knowledge_uploaded" 
                          class="cancel-upload-btn" 
                          @click="showCancelUploadDialog(file, 'private')"
                          title="撤销私有知识库上传">
                    ×
                  </button>
                </div>
              </div>
            </td>
            <td>{{ formatDate(file.uploaded_at) }}</td>
            <td class="action-column">
              <button class="action-btn download-btn" @click="downloadFile(file)">
                下载
              </button>
              <button class="action-btn view-btn" @click="viewFile(file)">
                查看
              </button>
              <button class="action-btn upload-btn" @click="showKnowledgeUploadDialog(file)">
                上传知识库
              </button>
              <button class="action-btn delete-btn" @click="deleteFile(file)">
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- 空状态 -->
      <div v-if="files.length === 0" class="empty-state">
        <p>暂无文档，请上传文档</p>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="pagination.total > 0" class="pagination">
      <button 
        :disabled="!pagination.has_prev" 
        @click="changePage(pagination.page - 1)"
      >
        上一页
      </button>
      <span class="page-info">
        第 {{ pagination.page }} 页，共 {{ pagination.pages }} 页
      </span>
      <button 
        :disabled="!pagination.has_next" 
        @click="changePage(pagination.page + 1)"
      >
        下一页
      </button>
    </div>

    <!-- 上传对话框 -->
    <div v-if="showDialog" class="dialog-overlay">
      <div class="dialog upload-dialog">
        <h3>上传文档</h3>
        <form @submit.prevent="uploadFile">
          <div class="form-group">
            <label>文件分类 *</label>
            <select v-model="uploadForm.file_category" required>
              <option value="case">案件文档</option>
              <option value="contract">合同文档</option>
              <option value="template">模板文档</option>
              <option value="general">普通文档</option>
            </select>
          </div>
          
          <div v-if="uploadForm.file_category === 'case'" class="case-fields">
            <div class="form-group">
              <label>案件主题 *</label>
              <input 
                v-model="uploadForm.case_subject"
                type="text" 
                placeholder="请输入案件主题"
                required
              />
            </div>
            
            <div class="form-group">
              <label>备注</label>
              <textarea 
                v-model="uploadForm.case_notes" 
                rows="3"
                placeholder="请简要描述案件情况"
              ></textarea>
            </div>
          </div>
          
          <div class="form-group">
            <label>选择文件 *</label>
            <div class="file-upload-area" 
                 @dragover.prevent="onDragOver" 
                 @dragleave.prevent="onDragLeave" 
                 @drop.prevent="onDrop"
                 :class="{ 'drag-over': isDragOver }">
              <input 
                ref="fileInput"
                type="file" 
                @change="handleFileSelect"
                accept=".pdf,.doc,.docx,.txt"
                multiple
                style="display: none;"
              />
              <div class="upload-content" @click="$refs.fileInput.click()">
                <div class="upload-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7,10 12,15 17,10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                </div>
                <div class="upload-text">
                  <p class="upload-title">点击选择文件或拖拽文件到此处</p>
                  <p class="upload-subtitle">支持 PDF、DOC、DOCX、TXT 格式，可选择多个文件</p>
                </div>
              </div>
              <div v-if="selectedFiles.length > 0" class="selected-files">
                <div class="files-summary">
                  <span>已选择 {{ selectedFiles.length }} 个文件</span>
                  <button type="button" @click="clearFiles">清空</button>
                </div>
                <div class="file-list">
                  <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
                    <span class="file-name">{{ file.name }}</span>
                    <span class="file-size">({{ formatFileSize(file.size) }})</span>
                    <button type="button" @click="removeFile(index)">×</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="uploadProgress.show" class="upload-progress">
            <div class="progress-header">
              <span>上传进度: {{ uploadProgress.completed }}/{{ uploadProgress.total }}</span>
              <span>{{ Math.round((uploadProgress.completed / uploadProgress.total) * 100) }}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: (uploadProgress.completed / uploadProgress.total) * 100 + '%' }"></div>
            </div>
            <div v-if="uploadProgress.currentFile" class="current-file">
              正在上传: {{ uploadProgress.currentFile }}
            </div>
            <div v-if="uploadProgress.errors.length > 0" class="upload-errors">
              <h4>处理结果:</h4>
              <ul>
                <li v-for="error in uploadProgress.errors" :key="error.filename" 
                    :class="{ 'error-warning': error.type === 'warning', 'error-danger': error.type !== 'warning' }">
                  {{ error.filename }}: {{ error.error }}
                </li>
              </ul>
            </div>
          </div>
          
          <div class="dialog-footer">
            <button type="button" class="cancel-btn" @click="closeDialog" :disabled="uploading">
              {{ uploading ? '上传中...' : '取消' }}
            </button>
            <button type="submit" class="confirm-btn" :disabled="uploading || selectedFiles.length === 0">
              {{ uploading ? '上传中...' : `确定上传 (${selectedFiles.length} 个文件)` }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 知识库上传选择对话框 -->
    <div v-if="showKnowledgeDialog" class="dialog-overlay">
      <div class="dialog knowledge-dialog">
        <h3>选择知识库类型</h3>
        <div class="knowledge-options">
          <div class="option-item">
            <input type="checkbox" id="public" value="public" v-model="selectedKnowledgeTypes">
            <label for="public">
              <div class="option-content">
                <h4>公有知识库</h4>
                <p>上传到公有知识库，所有用户都可以访问</p>
                <span class="status" :class="currentFile.public_knowledge_uploaded ? 'uploaded' : 'not-uploaded'">
                  {{ currentFile.public_knowledge_uploaded ? '已上传' : '未上传' }}
                </span>
              </div>
            </label>
          </div>
          <div class="option-item">
            <input type="checkbox" id="private" value="private" v-model="selectedKnowledgeTypes">
            <label for="private">
              <div class="option-content">
                <h4>私有知识库</h4>
                <p>上传到私有知识库，仅您可以访问</p>
                <span class="status" :class="currentFile.private_knowledge_uploaded ? 'uploaded' : 'not-uploaded'">
                  {{ currentFile.private_knowledge_uploaded ? '已上传' : '未上传' }}
                </span>
              </div>
            </label>
          </div>
        </div>
        <div class="dialog-footer">
          <button type="button" class="cancel-btn" @click="closeKnowledgeDialog">
            取消
          </button>
          <button type="button" class="confirm-btn" @click="confirmUploadToKnowledge" 
                  :disabled="selectedKnowledgeTypes.length === 0 || uploading">
            {{ uploading ? '上传中...' : '确认上传' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 撤销知识库上传确认对话框 -->
    <div v-if="showCancelDialog" class="dialog-overlay">
      <div class="dialog cancel-dialog">
        <h3>撤销知识库上传</h3>
        <div class="cancel-content">
          <p>确定要撤销文件 <strong>"{{ cancelFile.filename }}"</strong> 从 <strong>{{ getCancelTypeText() }}</strong> 的上传吗？</p>
          <div class="warning-note">
            <span class="warning-icon">⚠️</span>
            <span>撤销后，该文件将从对应知识库中移除，无法再通过知识库检索到此文件内容。</span>
          </div>
        </div>
        <div class="dialog-footer">
          <button type="button" class="cancel-btn" @click="closeCancelDialog">
            取消
          </button>
          <button type="button" class="confirm-btn danger" @click="confirmCancelUpload" 
                  :disabled="uploading">
            {{ uploading ? '撤销中...' : '确认撤销' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 查看文档对话框 -->
    <div v-if="showViewDialog" class="dialog-overlay">
      <div class="dialog view-dialog">
        <h3>文档详情</h3>
        <div class="file-details">
          <div class="detail-row">
            <label>文件名：</label>
            <span>{{ viewingFile.filename }}</span>
          </div>
          <div class="detail-row">
            <label>文件分类：</label>
            <span class="category-tag" :class="viewingFile.file_category">
              {{ getCategoryName(viewingFile.file_category) }}
            </span>
          </div>
          <div v-if="viewingFile.case_title" class="detail-row">
          <label>案件主题：</label>
          <span>{{ viewingFile.case_title }}</span>
        </div>
        <div v-if="viewingFile.case_summary" class="detail-row">
          <label>备注：</label>
          <div class="summary-content">{{ viewingFile.case_summary }}</div>
        </div>
          <div class="detail-row">
            <label>上传时间：</label>
            <span>{{ formatDate(viewingFile.uploaded_at) }}</span>
          </div>
          <div class="detail-row">
            <label>存储路径：</label>
            <span class="minio-path">{{ viewingFile.minio_path }}</span>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="cancel-btn" @click="closeViewDialog">关闭</button>
          <button class="confirm-btn" @click="downloadFile(viewingFile)">下载文件</button>
        </div>
      </div>
    </div>

    <!-- 批量上传知识库对话框 -->
    <div v-if="showBatchKnowledgeDialog" class="dialog-overlay">
      <div class="dialog knowledge-dialog">
        <h3>批量上传到知识库</h3>
        <div class="dialog-content">
          <p>已选择 {{ selectedFileIds.length }} 个文件</p>
          
          <div class="knowledge-options">
            <div class="option-item">
              <input type="checkbox" id="batch-public" value="public" v-model="selectedKnowledgeTypes">
              <label for="batch-public">
                <div class="option-content">
                  <h4>公有知识库</h4>
                  <p>上传到公有知识库，所有用户都可以访问</p>
                </div>
              </label>
            </div>
            <div class="option-item">
              <input type="checkbox" id="batch-private" value="private" v-model="selectedKnowledgeTypes">
              <label for="batch-private">
                <div class="option-content">
                  <h4>私有知识库</h4>
                  <p>上传到私有知识库，仅您可以访问</p>
                </div>
              </label>
            </div>
          </div>
          
          <div v-if="uploadProgress.show" class="upload-progress">
            <div class="progress-header">
              <span>上传进度: {{ uploadProgress.completed }}/{{ uploadProgress.total }}</span>
              <span>{{ Math.round((uploadProgress.completed / uploadProgress.total) * 100) }}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: (uploadProgress.completed / uploadProgress.total) * 100 + '%' }"></div>
            </div>
            <div v-if="uploadProgress.currentFile" class="current-file">
              正在处理: {{ uploadProgress.currentFile }}
            </div>
            <div v-if="uploadProgress.errors.length > 0" class="upload-errors">
              <h4>处理结果:</h4>
              <ul>
                <li v-for="error in uploadProgress.errors" :key="error.filename" 
                    :class="error.type === 'warning' ? 'error-warning' : 'error-danger'">
                  {{ error.filename }}: {{ getDetailedErrorMessage(error) }}
                </li>
              </ul>
            </div>
          </div>
          
          <div v-else-if="uploading" style="margin-top: 20px; padding: 10px; background-color: #f8f9fa; border-radius: 4px;">
            <p style="margin: 0; color: #007bff;">正在上传文件到知识库...</p>
          </div>
        </div>
        
        <div class="dialog-footer">
          <button v-if="!uploadProgress.isCompleted" type="button" class="cancel-btn" @click="closeBatchKnowledgeDialog" :disabled="uploading">
            取消
          </button>
          <button v-if="!uploadProgress.isCompleted" type="button" class="confirm-btn" @click="confirmBatchUploadToKnowledge" :disabled="uploading || selectedKnowledgeTypes.length === 0">
            {{ uploading ? '上传中...' : '确认上传' }}
          </button>
          <button v-if="uploadProgress.isCompleted" type="button" class="confirm-btn" @click="handleUploadComplete">
            确定
          </button>
        </div>
      </div>
    </div>

    <!-- 批量删除对话框 -->
    <div v-if="showBatchDeleteDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>批量删除文件</h3>
        <div class="dialog-content">
          <p>确定要删除选中的 {{ selectedFileIds.length }} 个文件吗？</p>
          <p class="warning-text">此操作将同时从本地和远程知识库中删除文件，且无法恢复！</p>
        </div>
        <div class="dialog-footer">
          <button class="cancel-btn" @click="closeBatchDeleteDialog" :disabled="uploading">取消</button>
          <button class="confirm-btn danger" @click="confirmBatchDelete" :disabled="uploading">
            {{ uploading ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'CaseManagement',
  data() {
    return {
      searchQuery: '',
      filterCategory: '',
      showDialog: false,
      showViewDialog: false,
      showKnowledgeDialog: false,
      showCancelDialog: false,
      showBatchKnowledgeDialog: false,
      showBatchDeleteDialog: false,
      uploading: false,
      selectedKnowledgeTypes: [],
      selectedFileIds: [],
      currentFile: {},
      cancelFile: {},
      cancelType: '',
      files: [],
      selectedFiles: [],
      viewingFile: {},
      isDragOver: false,
      editingFile: null, // 当前正在编辑的文件
      editingField: null, // 当前正在编辑的字段
      editForm: { // 编辑表单数据
        file_category: '',
        case_title: '',
        case_summary: ''
      },
      pagination: {
        page: 1,
        per_page: 10,
        total: 0,
        pages: 0,
        has_prev: false,
        has_next: false
      },
      uploadForm: {
        file_category: 'general',
        case_subject: '',
        case_notes: ''
      },
      uploadProgress: {
        show: false,
        total: 0,
        completed: 0,
        currentFile: '',
        errors: [],
        isCompleted: false
      }
    }
  },
  computed: {
    filteredFiles() {
      return this.files.filter(file => {
        const matchesSearch = file.filename.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                            (file.case_title && file.case_title.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
        (file.case_summary && file.case_summary.toLowerCase().includes(this.searchQuery.toLowerCase()))
        return matchesSearch
      })
    },
    isAllSelected() {
      return this.filteredFiles.length > 0 && this.selectedFileIds.length === this.filteredFiles.length
    },
    isIndeterminate() {
      return this.selectedFileIds.length > 0 && this.selectedFileIds.length < this.filteredFiles.length
    }
  },
  mounted() {
    this.loadFiles()
  },
  methods: {
    async loadFiles(page = 1) {
      try {
        const token = localStorage.getItem('access_token')
        const params = {
          page,
          per_page: this.pagination.per_page
        }
        
        if (this.filterCategory) {
          params.file_category = this.filterCategory
        }
        
        const response = await axios.get('/api/files', {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          params
        })
        
        if (response.data.success) {
          this.files = response.data.data.files
          this.pagination = response.data.data.pagination
          // 清空选中状态
          this.selectedFileIds = []
        }
      } catch (error) {
        console.error('加载文件列表失败:', error)
        this.$message?.error('加载文件列表失败')
      }
    },
    
    // 多选相关方法
    toggleSelectAll() {
      if (this.isAllSelected) {
        this.selectedFileIds = []
      } else {
        this.selectedFileIds = this.filteredFiles.map(file => file.id)
      }
    },
    
    showBatchKnowledgeUploadDialog() {
      if (this.selectedFileIds.length === 0) {
        this.$message?.warning('请先选择要上传的文件')
        return
      }
      this.showBatchKnowledgeDialog = true
      this.selectedKnowledgeTypes = []
    },
    
    closeBatchKnowledgeDialog() {
      this.showBatchKnowledgeDialog = false
      this.selectedKnowledgeTypes = []
      this.uploadProgress.show = false
      this.uploadProgress.isCompleted = false
    },
    
    handleUploadComplete() {
      // 关闭对话框并刷新页面
      this.closeBatchKnowledgeDialog()
      this.selectedFileIds = []
      this.loadFiles(this.pagination.page)
    },
    
    async confirmBatchUploadToKnowledge() {
      if (this.selectedKnowledgeTypes.length === 0) {
        this.$message?.warning('请选择知识库类型')
        return
      }
      
      this.uploading = true
      
      // 显示进度条
      this.uploadProgress.show = true
      this.uploadProgress.total = this.selectedFileIds.length
      this.uploadProgress.completed = 0
      this.uploadProgress.currentFile = ''
      this.uploadProgress.errors = []
      this.uploadProgress.isCompleted = false
      
      try {
        const token = localStorage.getItem('access_token')
        
        // 使用fetch进行流式请求
        const response = await fetch('/api/files/batch-upload-knowledge-progress', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            file_ids: this.selectedFileIds,
            knowledge_types: this.selectedKnowledgeTypes
          })
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        
        while (true) {
          const { done, value } = await reader.read()
          
          if (done) break
          
          buffer += decoder.decode(value, { stream: true })
          
          // 处理完整的数据行
          const lines = buffer.split('\n')
          buffer = lines.pop() // 保留不完整的行
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                if (data.type === 'progress') {
                  // 更新进度
                  this.uploadProgress.completed = data.completed
                  this.uploadProgress.currentFile = data.currentFile
                  
                  // 添加新的错误信息
                  if (data.errors && data.errors.length > 0) {
                    data.errors.forEach(error => {
                      // 检查是否已存在相同的错误
                      const existingError = this.uploadProgress.errors.find(
                        e => e.file_id === error.file_id
                      )
                      if (!existingError) {
                        this.uploadProgress.errors.push({
                          filename: error.filename,
                          error: error.error,
                          type: error.type || 'error'  // 传递错误类型
                        })
                      }
                    })
                  }
                } else if (data.type === 'complete') {
                  // 处理完成
                  const results = data.data
                  
                  // 不显示消息提醒
                  
                  // 更新成功文件的状态
                  if (results.success_files.length > 0) {
                    results.success_files.forEach(successFile => {
                      const file = this.files.find(f => f.id === successFile.file_id)
                      if (file) {
                        this.selectedKnowledgeTypes.forEach(knowledgeType => {
                          if (knowledgeType === 'public') {
                            file.public_knowledge_uploaded = true
                          } else if (knowledgeType === 'private') {
                            file.private_knowledge_uploaded = true
                          }
                        })
                      }
                    })
                  }
                  
                  // 标记上传完成，等待用户确认
                  this.uploadProgress.isCompleted = true
                  
                } else if (data.type === 'error') {
                  this.uploadProgress.show = false
                }
              } catch (parseError) {
                console.error('解析进度数据失败:', parseError)
              }
            }
          }
        }
        
        // 上传完成后不自动关闭对话框，等待用户确认
        // this.closeBatchKnowledgeDialog()
        // this.selectedFileIds = []
        // this.loadFiles(this.pagination.page)
      } catch (error) {
        console.error('批量上传失败:', error)
        this.uploadProgress.show = false
      } finally {
        this.uploading = false
      }
    },
    
    getDetailedErrorMessage(error) {
      // 直接返回后端提供的错误信息，因为后端已经包含了具体的知识库类型信息
      return error.error
    },
    
    showBatchDeleteConfirmDialog() {
      if (this.selectedFileIds.length === 0) {
        this.$message?.warning('请先选择要删除的文件')
        return
      }
      this.showBatchDeleteDialog = true
    },
    
    closeBatchDeleteDialog() {
      this.showBatchDeleteDialog = false
    },
    
    async confirmBatchDelete() {
      this.uploading = true
      const selectedFiles = this.files.filter(file => this.selectedFileIds.includes(file.id))
      let successCount = 0
      let failCount = 0
      
      try {
        for (const file of selectedFiles) {
          try {
            const token = localStorage.getItem('access_token')
            const response = await axios.delete(`/api/files/${file.id}`, {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            })
            
            if (response.data.success) {
              successCount++
            } else {
              failCount++
            }
          } catch (error) {
            console.error(`删除文件 ${file.filename} 失败:`, error)
            failCount++
          }
        }
        
        if (failCount === 0) {
          this.$message?.success(`批量删除成功，共删除 ${successCount} 个文件`)
        } else {
          this.$message?.warning(`批量删除完成，成功 ${successCount} 个，失败 ${failCount} 个`)
        }
        
        this.closeBatchDeleteDialog()
        this.selectedFileIds = []
        this.loadFiles(this.pagination.page)
      } catch (error) {
        console.error('批量删除失败:', error)
        this.$message?.error('批量删除失败')
      } finally {
        this.uploading = false
      }
    },
    
    showUploadDialog() {
      this.showDialog = true
      this.uploadForm = {
        file_category: 'general',
        case_subject: '',
        case_notes: ''
      }
      this.selectedFiles = []
      this.uploadProgress = {
        show: false,
        total: 0,
        completed: 0,
        currentFile: '',
        errors: [],
        isCompleted: false
      }
    },
    
    closeDialog() {
      this.showDialog = false
      this.uploadForm = {
        file_category: 'general',
        case_subject: '',
        case_notes: ''
      }
      this.selectedFiles = []
      this.uploadProgress = {
        show: false,
        total: 0,
        completed: 0,
        currentFile: '',
        errors: [],
        isCompleted: false
      }
    },
    
    handleFileSelect(event) {
      this.selectedFiles = Array.from(event.target.files)
    },
    
    clearFiles() {
      this.selectedFiles = []
      this.$refs.fileInput.value = ''
    },
    
    removeFile(index) {
      this.selectedFiles.splice(index, 1)
      if (this.selectedFiles.length === 0) {
        this.$refs.fileInput.value = ''
      }
    },
    
    onDragOver(event) {
      event.preventDefault()
      this.isDragOver = true
    },
    
    onDragLeave(event) {
      event.preventDefault()
      this.isDragOver = false
    },
    
    onDrop(event) {
      event.preventDefault()
      this.isDragOver = false
      const files = Array.from(event.dataTransfer.files)
      const allowedTypes = ['.pdf', '.doc', '.docx', '.txt']
      
      const validFiles = files.filter(file => {
        const extension = '.' + file.name.split('.').pop().toLowerCase()
        return allowedTypes.includes(extension)
      })
      
      if (validFiles.length > 0) {
        this.selectedFiles = [...this.selectedFiles, ...validFiles]
      }
      
      if (files.length > validFiles.length) {
        this.$message.warning('部分文件格式不支持，仅支持 PDF、DOC、DOCX、TXT 格式')
      }
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },
    
    // 编辑相关方法
    startEdit(file, field) {
      this.editingFile = file.id
      this.editingField = field
      this.editForm = {
        file_category: file.file_category,
        case_title: file.case_title || '',
        case_summary: file.case_summary || ''
      }
      
      // 添加编辑状态CSS类
      this.$nextTick(() => {
        const tableContainer = document.querySelector('.file-table')
        if (tableContainer) {
          tableContainer.classList.add('editing')
          console.log('已添加editing类:', tableContainer.classList.contains('editing'))
        } else {
          console.log('未找到.file-table元素')
        }
        
        // 延迟聚焦到输入框
        const editInput = this.$refs.editInput
        if (editInput && editInput[0]) {
          editInput[0].focus()
        }
      })
    },
    
    cancelEdit() {
      this.editingFile = null
      this.editingField = null
      this.editForm = {
        file_category: '',
        case_title: '',
        case_summary: ''
      }
      
      // 移除编辑状态CSS类
      const tableContainer = document.querySelector('.file-table')
      if (tableContainer) {
        tableContainer.classList.remove('editing')
        console.log('已移除editing类:', !tableContainer.classList.contains('editing'))
      } else {
        console.log('未找到.file-table元素')
      }
    },
    
    async saveEdit(file) {
      if (this.editingFile !== file.id) return
      
      try {
        const token = localStorage.getItem('access_token')
        const response = await axios.put(`/api/files/${file.id}`, this.editForm, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })
        
        if (response.data.success) {
          // 更新本地文件数据
          const updatedFile = response.data.data
          const fileIndex = this.files.findIndex(f => f.id === file.id)
          if (fileIndex !== -1) {
            this.files[fileIndex] = { ...this.files[fileIndex], ...updatedFile }
          }
          
          this.$message?.success('文件信息更新成功')
          this.cancelEdit()
        } else {
          this.$message?.error(response.data.message || '更新失败')
        }
      } catch (error) {
        console.error('更新文件信息失败:', error)
        let errorMessage = '更新文件信息失败'
        if (error.response) {
          errorMessage = error.response.data?.message || `服务器错误: ${error.response.status}`
        } else if (error.request) {
          errorMessage = '网络连接失败，请检查后端服务是否启动'
        } else {
          errorMessage = error.message || '未知错误'
        }
        this.$message?.error(errorMessage)
      }
    },
    
    async uploadFile() {
      if (this.selectedFiles.length === 0) {
        this.$message?.error('请选择文件')
        return
      }
      
      if (this.uploadForm.file_category === 'case' && !this.uploadForm.case_subject) {
        this.$message?.error('案件文档必须填写案件主题')
        return
      }
      
      this.uploading = true
      this.uploadProgress.show = true
      this.uploadProgress.total = this.selectedFiles.length
      this.uploadProgress.completed = 0
      this.uploadProgress.errors = []
      
      try {
        const formData = new FormData()
        
        // 添加所有文件
        this.selectedFiles.forEach(file => {
          formData.append('files', file)
        })
        
        formData.append('file_category', this.uploadForm.file_category)
        
        if (this.uploadForm.file_category === 'case') {
          formData.append('case_subject', this.uploadForm.case_subject)
      formData.append('case_notes', this.uploadForm.case_notes)
        }
        
        const token = localStorage.getItem('access_token')
        const response = await axios.post('/api/files/batch-upload', formData, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        })
        
        if (response.data.success) {
          const { successful_files, failed_files } = response.data.data
          
          this.uploadProgress.completed = successful_files.length
          this.uploadProgress.errors = failed_files.map(f => ({
            filename: f.filename,
            message: f.error
          }))
          
          if (failed_files.length === 0) {
            setTimeout(() => {
              this.closeDialog()
              this.loadFiles()
            }, 1500)
          }
        } else {
          this.$message?.error(response.data.message || '上传失败')
        }
      } catch (error) {
        console.error('文件上传失败:', error)
        let errorMessage = '文件上传失败'
        if (error.response) {
          errorMessage = error.response.data?.message || `服务器错误: ${error.response.status}`
          console.error('服务器响应:', error.response.data)
        } else if (error.request) {
          errorMessage = '网络连接失败，请检查后端服务是否启动'
          console.error('网络错误:', error.request)
        } else {
          errorMessage = error.message || '未知错误'
        }
        this.$message?.error(errorMessage)
        this.uploadProgress.errors.push({
          filename: '批量上传',
          message: errorMessage
        })
      } finally {
        this.uploading = false
      }
    },
    
    async downloadFile(file) {
      try {
        const token = localStorage.getItem('access_token')
        const response = await axios.get(`/api/files/${file.id}/download`, {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          responseType: 'blob'
        })
        
        // 创建下载链接
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', file.filename)
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
        
        this.$message?.success('文件正在下载')
      } catch (error) {
        console.error('文件下载失败:', error)
        this.$message?.error('文件下载失败')
      }
    },
    
    viewFile(file) {
      this.viewingFile = file
      this.showViewDialog = true
    },
    
    closeViewDialog() {
      this.showViewDialog = false
      this.viewingFile = {}
    },
    
    async deleteFile(file) {
      if (!confirm(`确定要删除文件 "${file.filename}" 吗？`)) {
        return
      }
      
      try {
        const token = localStorage.getItem('access_token')
        const response = await axios.delete(`/api/files/${file.id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.data.success) {
          this.$message?.success('文件删除成功')
          this.loadFiles()
        } else {
          this.$message?.error(response.data.message || '删除失败')
        }
      } catch (error) {
        console.error('文件删除失败:', error)
        this.$message?.error('文件删除失败')
      }
    },
    
    changePage(page) {
      this.loadFiles(page)
    },
    
    getCategoryName(category) {
      const categoryMap = {
        'case': '案件文档',
        'contract': '合同文档',
        'template': '模板文档',
        'general': '普通文档'
      }
      return categoryMap[category] || category
    },
    
    formatDate(dateString) {
      if (!dateString) return '-'
      return new Date(dateString).toLocaleString('zh-CN')
    },
    
    getKnowledgeStatus(file, type) {
      const isUploaded = type === 'public' ? file.public_knowledge_uploaded : file.private_knowledge_uploaded
      return isUploaded ? 'uploaded' : 'not-uploaded'
    },
    
    getKnowledgeStatusText(file, type) {
      const isUploaded = type === 'public' ? file.public_knowledge_uploaded : file.private_knowledge_uploaded
      const prefix = type === 'public' ? '公用' : '私有'
      return isUploaded ? `${prefix}已上传` : `${prefix}未上传`
    },
    
    showKnowledgeUploadDialog(file) {
      this.currentFile = file
      this.selectedKnowledgeTypes = []
      this.showKnowledgeDialog = true
    },
    
    closeKnowledgeDialog() {
      this.showKnowledgeDialog = false
      this.currentFile = {}
      this.selectedKnowledgeTypes = []
    },
    
    async confirmUploadToKnowledge() {
      if (this.selectedKnowledgeTypes.length === 0) {
        this.$message?.warning('请至少选择一个知识库类型')
        return
      }
      
      // 检查是否已经上传过，过滤掉已上传的类型
      const typesToUpload = this.selectedKnowledgeTypes.filter(type => {
        if (type === 'public' && this.currentFile.public_knowledge_uploaded) {
          return false
        }
        if (type === 'private' && this.currentFile.private_knowledge_uploaded) {
          return false
        }
        return true
      })
      
      if (typesToUpload.length === 0) {
        this.$message?.warning('所选知识库类型均已上传')
        return
      }
      
      this.uploading = true
      
      try {
        const token = localStorage.getItem('access_token')
        const response = await axios.post(`/api/files/${this.currentFile.id}/upload-knowledge`, {
          knowledge_types: typesToUpload
        }, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.data.success) {
          const typeNames = typesToUpload.map(type => type === 'public' ? '公有知识库' : '私有知识库')
          this.$message?.success(`文件已成功上传到${typeNames.join('和')}`)
          this.loadFiles() // 重新加载文件列表以更新状态
          this.closeKnowledgeDialog()
        } else {
          this.$message?.error(response.data.message || '上传知识库失败')
        }
      } catch (error) {
        console.error('上传知识库失败:', error)
        this.$message?.error('上传知识库失败')
      } finally {
        this.uploading = false
      }
    },
    
    // 撤销上传相关方法
    showCancelUploadDialog(file, type) {
      this.cancelFile = file
      this.cancelType = type
      this.showCancelDialog = true
    },
    
    closeCancelDialog() {
      this.showCancelDialog = false
      this.cancelFile = {}
      this.cancelType = ''
    },
    
    getCancelTypeText() {
      return this.cancelType === 'public' ? '公有知识库' : '私有知识库'
    },
    
    async confirmCancelUpload() {
      if (!this.cancelFile.id || !this.cancelType) {
        this.$message?.error('参数错误')
        return
      }
      
      this.uploading = true
      
      try {
        const token = localStorage.getItem('access_token')
        const response = await axios.post(`/api/files/${this.cancelFile.id}/cancel-knowledge`, {
          knowledge_types: [this.cancelType]
        }, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.data.success) {
          const typeName = this.cancelType === 'public' ? '公有知识库' : '私有知识库'
          this.$message?.success(`已成功撤销文件从${typeName}的上传`)
          this.loadFiles() // 重新加载文件列表以更新状态
          this.closeCancelDialog()
        } else {
          this.$message?.error(response.data.message || '撤销上传失败')
        }
      } catch (error) {
        console.error('撤销上传失败:', error)
        let errorMessage = '撤销上传失败'
        if (error.response) {
          errorMessage = error.response.data?.message || `服务器错误: ${error.response.status}`
        } else if (error.request) {
          errorMessage = '网络连接失败，请检查后端服务是否启动'
        } else {
          errorMessage = error.message || '未知错误'
        }
        this.$message?.error(errorMessage)
      } finally {
        this.uploading = false
      }
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
  }
}
</script>

<style scoped>
.case-management {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.page-header h2 {
  margin: 0;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 15px;
  align-items: center;
}

.search-box input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 200px;
}

.filter-box select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
}

.add-button {
  background: #007bff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}

.add-button:hover {
  background: #0056b3;
}

.file-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.file-table table {
  width: 100%;
  border-collapse: collapse;
}

.file-table th,
.file-table td {
  padding: 12px;
  text-align: center;
  border-bottom: 1px solid #eee;
  vertical-align: middle;
}

.file-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.category-tag {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.category-tag.case {
  background: #e3f2fd;
  color: #1976d2;
}

.category-tag.contract {
  background: #f3e5f5;
  color: #7b1fa2;
}

.category-tag.template {
  background: #e8f5e8;
  color: #388e3c;
}

.category-tag.general {
  background: #fff3e0;
  color: #f57c00;
}

.summary-cell {
  max-width: 200px;
}

.summary-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-column {
  white-space: nowrap;
}

.action-btn {
  padding: 4px 8px;
  margin: 0 2px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
}

.download-btn {
  background: #28a745;
  color: white;
}

.view-btn {
  background: #17a2b8;
  color: white;
}

.delete-btn {
  background: #dc3545;
  color: white;
}

.upload-btn {
  background: #409eff;
  color: white;
}

.upload-btn:hover {
  background: #66b1ff;
}

.upload-btn:disabled {
  background: #c0c4cc;
  cursor: not-allowed;
}

.action-btn:hover {
  opacity: 0.8;
}

.knowledge-status {
  text-align: center;
  vertical-align: middle;
  padding: 8px;
}

.status-tags {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  justify-content: center;
  min-height: 60px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
}

.cancel-upload-btn {
  background: #ff4d4f;
  color: white;
  border: none;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: all 0.2s ease;
  opacity: 0.7;
}

.cancel-upload-btn:hover {
  opacity: 1;
  background: #ff7875;
  transform: scale(1.1);
}

.cancel-upload-btn:active {
  transform: scale(0.95);
}

.status-tag {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  min-width: 70px;
  text-align: center;
  white-space: nowrap;
}

.status-tag.uploaded {
  background: #f0f9ff;
  color: #1890ff;
  border: 1px solid #d1ecf1;
}

.status-tag.not-uploaded {
  background: #fff2f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

/* 知识库选择对话框样式 */
.knowledge-dialog {
  width: 500px;
  max-width: 90vw;
}

/* 撤销上传对话框样式 */
.cancel-dialog {
  width: 450px;
  max-width: 90vw;
}

.cancel-content {
  margin: 20px 0;
}

.cancel-content p {
  margin: 0 0 15px 0;
  color: #333;
  line-height: 1.5;
}

.warning-note {
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.warning-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.warning-note span:last-child {
  color: #d46b08;
  font-size: 14px;
  line-height: 1.4;
}

.confirm-btn.danger {
  background: #ff4d4f;
}

.confirm-btn.danger:not(:disabled):hover {
  background: #ff7875;
}

.knowledge-options {
  margin: 20px 0;
}

.option-item {
  margin-bottom: 15px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  transition: all 0.3s ease;
  position: relative;
}

.option-item:hover {
  border-color: #409eff;
}

.option-item input[type="checkbox"] {
  display: none;
}

.option-item input[type="checkbox"]:checked + label {
  border-color: #409eff !important;
  background: #f0f9ff !important;
}

.option-item input[type="checkbox"]:checked + label .option-content {
  background: transparent;
}

.option-item input[type="checkbox"]:checked + label::before,
.option-item input[type="checkbox"]:checked + label::after {
  display: none;
}

.option-item label {
  display: block;
  padding: 15px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.option-content h4 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 16px;
  font-weight: 600;
}

.option-content p {
  margin: 0 0 10px 0;
  color: #666;
  font-size: 14px;
  line-height: 1.4;
}

.option-content .status {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.option-content .status.uploaded {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.option-content .status.not-uploaded {
  background: #fff2f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination button:not(:disabled):hover {
  background: #f8f9fa;
}

/* 编辑功能样式 */
.editable-cell {
  cursor: pointer;
  position: relative;
}

.editable-cell:hover {
  background-color: #f8f9fa;
}

.edit-mode {
  padding: 0;
}

.view-mode {
  padding: 8px;
  min-height: 20px;
}

.edit-input {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid #409eff;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
  background: white;
}

.edit-textarea {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid #409eff;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
  background: white;
  resize: vertical;
  min-height: 40px;
}

.edit-select {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid #409eff;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
  background: white;
}

.edit-input:focus,
.edit-textarea:focus,
.edit-select:focus {
  border-color: #66b1ff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

/* 提示文本 */
.editable-cell::after {
  content: '双击编辑';
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  font-size: 12px;
  color: #999;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

/* 只在非编辑状态下显示提示 */
.editable-cell:hover::after {
  opacity: 1;
}

/* 当处于编辑状态时，隐藏所有提示文字 */
.file-table.editing .editable-cell::after {
  display: none !important;
  opacity: 0 !important;
}

.file-table.editing .editable-cell:hover::after {
  opacity: 0 !important;
  display: none !important;
  content: none !important;
}

/* 编辑状态下禁用hover背景色变化 */
.file-table.editing .editable-cell:hover {
  background-color: transparent !important;
}

/* 更强的选择器优先级 */
.file-table.editing td.editable-cell::after {
  display: none !important;
  opacity: 0 !important;
  content: none !important;
}

.file-table.editing td.editable-cell:hover::after {
  display: none !important;
  opacity: 0 !important;
  content: none !important;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.dialog {
  background: white;
  border-radius: 8px;
  padding: 20px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.dialog h3 {
  margin: 0 0 20px 0;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-group textarea {
  resize: vertical;
}

.file-upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 0;
  text-align: center;
  background: #f9fafb;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.file-upload-area:hover {
  border-color: #3b82f6;
  background: #eff6ff;
}

.file-upload-area.drag-over {
  border-color: #10b981;
  background: #ecfdf5;
  transform: scale(1.02);
}

.upload-content {
  padding: 40px 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-content:hover {
  background: rgba(59, 130, 246, 0.05);
}

.upload-icon {
  margin-bottom: 16px;
  color: #6b7280;
  transition: color 0.2s ease;
}

.file-upload-area:hover .upload-icon {
  color: #3b82f6;
}

.file-upload-area.drag-over .upload-icon {
  color: #10b981;
}

.upload-text {
  margin: 0;
}

.upload-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 8px 0;
}

.upload-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
  line-height: 1.4;
}

.selected-file {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #e3f2fd;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 10px;
}

.selected-file button {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 16px;
}

.case-fields {
  border: 1px solid #e3f2fd;
  border-radius: 4px;
  padding: 15px;
  margin: 15px 0;
  background: #f8f9ff;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.cancel-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.confirm-btn {
  padding: 8px 16px;
  border: none;
  background: #007bff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
}

.confirm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-btn:hover {
  background: #f8f9fa;
}

.confirm-btn:not(:disabled):hover {
  background: #0056b3;
}

.file-details {
  margin: 20px 0;
}

.detail-row {
  display: flex;
  margin-bottom: 10px;
  align-items: flex-start;
}

.detail-row label {
  min-width: 100px;
  font-weight: 500;
  color: #333;
}

.summary-content {
  flex: 1;
  background: #f8f9fa;
  padding: 8px;
  border-radius: 4px;
  white-space: pre-wrap;
}

.minio-path {
  font-family: monospace;
  background: #f8f9fa;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  word-break: break-all;
}



.selected-files {
  margin-top: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  background: #ffffff;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}

.files-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
  font-weight: 600;
  color: #374151;
}

.files-summary button {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
}

.files-summary button:hover {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
}

.file-list {
  max-height: 200px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.file-item:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.file-item:last-child {
  margin-bottom: 0;
}

.file-name {
  flex: 1;
  font-weight: 500;
  margin-right: 12px;
  word-break: break-all;
  color: #374151;
}

.file-size {
  color: #6b7280;
  font-size: 12px;
  margin-right: 12px;
  font-weight: 500;
}

.file-item button {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
}

.file-item button:hover {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
}

.upload-progress {
  margin: 20px 0;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: 500;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #e9ecef;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #28a745, #20c997);
  transition: width 0.3s ease;
}

.current-file {
  color: #666;
  font-size: 14px;
  margin-bottom: 10px;
}

.upload-errors {
  margin-top: 15px;
  padding: 10px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  color: #495057;
}

.upload-errors h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
}

.upload-errors ul {
  margin: 0;
  padding-left: 20px;
}

.upload-errors li {
  margin-bottom: 5px;
  font-size: 13px;
}

.upload-errors .error-warning {
  color: #856404;
  background: #fff3cd;
  border-left: 3px solid #ffc107;
  padding: 5px 8px;
  margin: 3px 0;
  border-radius: 3px;
}

.upload-errors .error-danger {
  color: #721c24;
  background: #f8d7da;
  border-left: 3px solid #dc3545;
  padding: 5px 8px;
  margin: 3px 0;
  border-radius: 3px;
}

/* 批量操作样式 */
.batch-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.batch-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.3s ease;
}

.batch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.batch-btn i {
  font-size: 12px;
}

.batch-btn.upload-btn {
  background: #007bff;
  color: white;
}

.batch-btn.upload-btn:hover:not(:disabled) {
  background: #0056b3;
}

.batch-btn.delete-btn {
  background: #dc3545;
  color: white;
}

.batch-btn.delete-btn:hover:not(:disabled) {
  background: #c82333;
}

.selected-count {
  color: #666;
  font-size: 14px;
  margin-right: 10px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-item input[type="checkbox"] {
  margin: 0;
}

.checkbox-item span {
  font-size: 14px;
}

/* 警告文本样式 */
.warning-text {
  color: #dc3545;
  font-size: 14px;
  margin-top: 10px;
  font-weight: 500;
}

/* 危险按钮样式 */
.confirm-btn.danger {
  background: #dc3545;
}

.confirm-btn.danger:hover:not(:disabled) {
  background: #c82333;
}
</style>