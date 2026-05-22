<template>
  <div class="data-resource-page">
    <header class="page-header">
      <div class="title-area">
        <h1>数据资源管理</h1>
        <p>统一管理数据集与任务模板，为群组协同计算提供资源支撑</p>
      </div>
    </header>

    <main class="page-content">
      <el-card shadow="never" class="table-card">
        <el-tabs v-model="activeTab" class="custom-tabs">
          <el-tab-pane label="数据集管理" name="dataset">
            <div class="toolbar">
              <el-form :inline="true" :model="datasetQuery">
                <el-form-item label="所属机构">
                  <el-select v-model="datasetQuery.agency_id" placeholder="全部机构" clearable filterable style="width: 200px">
                    <el-option v-for="a in agencyList" :key="a.id" :label="a.agency_name" :value="a.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="关键词">
                  <el-input v-model="datasetQuery.keyword" placeholder="名称或编码" clearable style="width: 200px" @keyup.enter="loadDatasets" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="loadDatasets">查询</el-button>
                  <el-button type="success" @click="openDatasetDialog()">新增数据集</el-button>
                </el-form-item>
              </el-form>
            </div>
            <el-table :data="datasetList" v-loading="datasetLoading" border stripe>
              <el-table-column prop="dataset_name" label="数据集名称" min-width="180" />
              <el-table-column prop="agency_name" label="所属机构" width="160" />
              <el-table-column prop="node_name" label="所属节点" width="140" />
              <el-table-column label="数据类型" width="100" align="center">
                <template #default="{ row }">
                  <el-tag size="small">{{ dataTypeLabel(row.data_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="data_location" label="数据位置" min-width="200" show-overflow-tooltip />
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="openDatasetDialog(row)">详情</el-button>
                  <el-button type="primary" link size="small" @click="openDatasetDialog(row, true)">编辑</el-button>
                  <el-button type="danger" link size="small" @click="handleDeleteDataset(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-wrapper">
              <el-pagination background layout="total, prev, pager, next" :total="datasetTotal" :page-size="datasetQuery.page_size" v-model:current-page="datasetQuery.page" @current-change="loadDatasets" />
            </div>
          </el-tab-pane>

          <el-tab-pane label="任务模板管理" name="template">
            <div class="toolbar">
              <el-form :inline="true" :model="templateQuery">
                <el-form-item label="所属机构">
                  <el-select v-model="templateQuery.agency_id" placeholder="全部机构" clearable filterable style="width: 200px">
                    <el-option v-for="a in agencyList" :key="a.id" :label="a.agency_name" :value="a.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="关键词">
                  <el-input v-model="templateQuery.keyword" placeholder="名称或编码" clearable style="width: 200px" @keyup.enter="loadTemplates" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="loadTemplates">查询</el-button>
                  <el-button type="success" @click="openTemplateDialog()">新增模板</el-button>
                </el-form-item>
              </el-form>
            </div>
            <el-table :data="templateList" v-loading="templateLoading" border stripe>
              <el-table-column prop="template_name" label="模板名称" min-width="180" />
              <el-table-column prop="agency_name" label="所属机构" width="160" />
              <el-table-column label="适用场景" width="160">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.scenario || '-' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="执行方式" width="100" align="center">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.exec_mode === 'auto' ? '自动' : '手动' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="output_type" label="输出结果类型" width="140" />
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="openTemplateDialog(row)">详情</el-button>
                  <el-button type="primary" link size="small" @click="openTemplateDialog(row, true)">编辑</el-button>
                  <el-button type="danger" link size="small" @click="handleDeleteTemplate(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-wrapper">
              <el-pagination background layout="total, prev, pager, next" :total="templateTotal" :page-size="templateQuery.page_size" v-model:current-page="templateQuery.page" @current-change="loadTemplates" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <el-dialog v-model="datasetDialogVisible" :title="datasetIsEdit ? '编辑数据集' : (datasetForm.id ? '数据集详情' : '新增数据集')" width="600px">
        <el-form ref="datasetFormRef" :model="datasetForm" :rules="datasetRules" label-width="100px">
          <el-form-item label="数据集名称" prop="dataset_name">
            <el-input v-model="datasetForm.dataset_name" :disabled="!datasetIsEdit" />
          </el-form-item>
          <el-form-item label="所属机构" prop="agency_id">
            <el-select v-model="datasetForm.agency_id" :disabled="!datasetIsEdit" filterable style="width: 100%">
              <el-option v-for="a in agencyList" :key="a.id" :label="a.agency_name" :value="a.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="所属节点">
            <el-select v-model="datasetForm.node_id" :disabled="!datasetIsEdit" filterable clearable style="width: 100%">
              <el-option v-for="n in nodeList" :key="n.id" :label="n.node_name" :value="n.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="数据类型">
            <el-select v-model="datasetForm.data_type" :disabled="!datasetIsEdit" style="width: 100%">
              <el-option label="文件" value="file" />
              <el-option label="数据库表" value="database" />
              <el-option label="接口" value="api" />
            </el-select>
          </el-form-item>
          <el-form-item label="数据位置">
            <el-input v-model="datasetForm.data_location" :disabled="!datasetIsEdit" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="datasetForm.description" type="textarea" :rows="3" :disabled="!datasetIsEdit" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="datasetDialogVisible = false">取消</el-button>
          <el-button v-if="datasetIsEdit" type="primary" :loading="datasetSaving" @click="handleSaveDataset">保存</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="templateDialogVisible" :title="templateIsEdit ? '编辑模板' : (templateForm.id ? '模板详情' : '新增模板')" width="600px">
        <el-form ref="templateFormRef" :model="templateForm" :rules="templateRules" label-width="100px">
          <el-form-item label="模板名称" prop="template_name">
            <el-input v-model="templateForm.template_name" :disabled="!templateIsEdit" />
          </el-form-item>
          <el-form-item label="所属机构">
            <el-select v-model="templateForm.agency_id" :disabled="!templateIsEdit" filterable clearable style="width: 100%">
              <el-option v-for="a in agencyList" :key="a.id" :label="a.agency_name" :value="a.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="适用场景">
            <el-input v-model="templateForm.scenario" :disabled="!templateIsEdit" />
          </el-form-item>
          <el-form-item label="执行方式">
            <el-select v-model="templateForm.exec_mode" :disabled="!templateIsEdit" style="width: 100%">
              <el-option label="自动" value="auto" />
              <el-option label="手动" value="manual" />
            </el-select>
          </el-form-item>
          <el-form-item label="输出结果类型">
            <el-input v-model="templateForm.output_type" :disabled="!templateIsEdit" />
          </el-form-item>
          <el-form-item label="模板简介">
            <el-input v-model="templateForm.description" type="textarea" :rows="3" :disabled="!templateIsEdit" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="templateDialogVisible = false">取消</el-button>
          <el-button v-if="templateIsEdit" type="primary" :loading="templateSaving" @click="handleSaveTemplate">保存</el-button>
        </template>
      </el-dialog>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { getDatasetList, getDataset, createDataset, updateDataset, deleteDataset, type DatasetItem } from '@/api/dataset'
import { getStatTemplateList, getStatTemplate, createStatTemplate, updateStatTemplate, deleteStatTemplate, type StatTemplateItem } from '@/api/statTemplate'
import { getAgencyList } from '@/api/agency'
import { getNodeList } from '@/api/node'

const activeTab = ref('dataset')

const agencyList = ref<any[]>([])
const nodeList = ref<any[]>([])

const datasetList = ref<DatasetItem[]>([])
const datasetTotal = ref(0)
const datasetLoading = ref(false)
const datasetQuery = reactive({ page: 1, page_size: 10, keyword: '', agency_id: null as number | null })

const templateList = ref<StatTemplateItem[]>([])
const templateTotal = ref(0)
const templateLoading = ref(false)
const templateQuery = reactive({ page: 1, page_size: 10, keyword: '', agency_id: null as number | null })

const datasetDialogVisible = ref(false)
const datasetIsEdit = ref(false)
const datasetSaving = ref(false)
const datasetFormRef = ref<FormInstance>()
const datasetForm = reactive({ id: null as number | null, dataset_code: '', dataset_name: '', agency_id: null as number | null, node_id: null as number | null, data_type: 'file', data_location: '', description: '' })
const datasetRules: FormRules = { dataset_name: [{ required: true, message: '请输入数据集名称', trigger: 'blur' }], agency_id: [{ required: true, message: '请选择所属机构', trigger: 'change' }] }

const templateDialogVisible = ref(false)
const templateIsEdit = ref(false)
const templateSaving = ref(false)
const templateFormRef = ref<FormInstance>()
const templateForm = reactive({ id: null as number | null, template_code: '', template_name: '', agency_id: null as number | null, scenario: '', exec_mode: 'auto', output_type: '', description: '' })
const templateRules: FormRules = { template_name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }] }

function unwrapResponse(res: any) { return res?.data?.data ?? res?.data ?? res }

function dataTypeLabel(type: string | null) {
  const map: Record<string, string> = { file: '文件', database: '数据库表', api: '接口' }
  return map[type || 'file'] || type || '文件'
}

async function loadAgencies() {
  try {
    const res = await getAgencyList({ page: 1, page_size: 100 })
    const data = unwrapResponse(res)
    agencyList.value = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
  } catch (e) { console.error(e) }
}

async function loadNodes() {
  try {
    const res = await getNodeList({ page: 1, page_size: 100 })
    const data = unwrapResponse(res)
    const nodes = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
    nodeList.value = nodes.map(n => ({
      ...n,
      id: Number(n.id)
    }))
    console.log('Loaded nodes:', nodeList.value)
  } catch (e) { console.error(e) }
}

async function loadDatasets() {
  datasetLoading.value = true
  try {
    const res = await getDatasetList({ ...datasetQuery, agency_id: datasetQuery.agency_id || undefined })
    const data = unwrapResponse(res)
    datasetList.value = data?.items || []
    datasetTotal.value = data?.total || 0
  } catch (e) { ElMessage.error('数据集加载失败') }
  finally { datasetLoading.value = false }
}

async function loadTemplates() {
  templateLoading.value = true
  try {
    const res = await getStatTemplateList({ ...templateQuery, agency_id: templateQuery.agency_id || undefined })
    const data = unwrapResponse(res)
    templateList.value = data?.items || []
    templateTotal.value = data?.total || 0
  } catch (e) { ElMessage.error('模板加载失败') }
  finally { templateLoading.value = false }
}

async function openDatasetDialog(row?: DatasetItem, edit = false) {
  if (nodeList.value.length === 0) {
    await loadNodes()
  }
  
  if (row) {
    datasetForm.id = row.id
    datasetForm.dataset_code = row.dataset_code
    datasetForm.dataset_name = row.dataset_name
    datasetForm.agency_id = row.agency_id
    datasetForm.node_id = row.node_id ? Number(row.node_id) : null
    datasetForm.data_type = row.data_type || 'file'
    datasetForm.data_location = row.data_location || ''
    datasetForm.description = row.description || ''
    datasetIsEdit.value = edit
    console.log('Open dataset dialog:', {
      row_node_id: row.node_id,
      form_node_id: datasetForm.node_id,
      node_list_ids: nodeList.value.map(n => n.id),
      matched: nodeList.value.find(n => n.id === Number(row.node_id))
    })
  } else {
    datasetForm.id = null
    datasetForm.dataset_code = ''
    datasetForm.dataset_name = ''
    datasetForm.agency_id = null
    datasetForm.node_id = null
    datasetForm.data_type = 'file'
    datasetForm.data_location = ''
    datasetForm.description = ''
    datasetIsEdit.value = true
  }
  datasetDialogVisible.value = true
}

async function handleSaveDataset() {
  if (!datasetFormRef.value) return
  await datasetFormRef.value.validate(async (valid) => {
    if (!valid) return
    datasetSaving.value = true
    try {
      if (datasetForm.id) {
        const updateData: any = { dataset_name: datasetForm.dataset_name }
        if (datasetForm.node_id !== null) updateData.node_id = datasetForm.node_id
        if (datasetForm.data_type) updateData.data_type = datasetForm.data_type
        if (datasetForm.data_location) updateData.data_location = datasetForm.data_location
        if (datasetForm.description) updateData.description = datasetForm.description
        console.log('Update dataset payload:', updateData)
        await updateDataset(datasetForm.id, updateData)
        ElMessage.success('数据集更新成功')
      } else {
        const code = `DS_${Date.now()}`
        const createData = {
          dataset_code: code,
          dataset_name: datasetForm.dataset_name,
          agency_id: datasetForm.agency_id!,
          node_id: datasetForm.node_id,
          data_type: datasetForm.data_type,
          data_location: datasetForm.data_location,
          storage_uri: datasetForm.data_location,
          description: datasetForm.description
        }
        console.log('Create dataset payload:', createData)
        await createDataset(createData)
        ElMessage.success('数据集创建成功')
      }
      datasetDialogVisible.value = false
      await loadDatasets()
    } catch (e: any) { 
      console.error('Save dataset error:', e)
      ElMessage.error(e?.response?.data?.detail || '操作失败') 
    }
    finally { datasetSaving.value = false }
  })
}

async function handleDeleteDataset(row: DatasetItem) {
  await ElMessageBox.confirm(`确认删除数据集「${row.dataset_name}」吗？`, '删除确认', { type: 'warning' })
  try {
    await deleteDataset(row.id)
    ElMessage.success('删除成功')
    await loadDatasets()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '删除失败') }
}

function openTemplateDialog(row?: StatTemplateItem, edit = false) {
  if (row) {
    templateForm.id = row.id
    templateForm.template_code = row.template_code
    templateForm.template_name = row.template_name
    templateForm.agency_id = row.agency_id
    templateForm.scenario = row.scenario || ''
    templateForm.exec_mode = row.exec_mode || 'auto'
    templateForm.output_type = row.output_type || ''
    templateForm.description = row.description || ''
    templateIsEdit.value = edit
  } else {
    templateForm.id = null
    templateForm.template_code = ''
    templateForm.template_name = ''
    templateForm.agency_id = null
    templateForm.scenario = ''
    templateForm.exec_mode = 'auto'
    templateForm.output_type = ''
    templateForm.description = ''
    templateIsEdit.value = true
  }
  templateDialogVisible.value = true
}

async function handleSaveTemplate() {
  if (!templateFormRef.value) return
  await templateFormRef.value.validate(async (valid) => {
    if (!valid) return
    templateSaving.value = true
    try {
      if (templateForm.id) {
        await updateStatTemplate(templateForm.id, { template_name: templateForm.template_name, scenario: templateForm.scenario, exec_mode: templateForm.exec_mode, output_type: templateForm.output_type, description: templateForm.description })
        ElMessage.success('模板更新成功')
      } else {
        const code = `TPL_${Date.now()}`
        await createStatTemplate({ template_code: code, template_name: templateForm.template_name, agency_id: templateForm.agency_id || undefined, scenario: templateForm.scenario, exec_mode: templateForm.exec_mode, output_type: templateForm.output_type, description: templateForm.description })
        ElMessage.success('模板创建成功')
      }
      templateDialogVisible.value = false
      await loadTemplates()
    } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
    finally { templateSaving.value = false }
  })
}

async function handleDeleteTemplate(row: StatTemplateItem) {
  await ElMessageBox.confirm(`确认删除模板「${row.template_name}」吗？`, '删除确认', { type: 'warning' })
  try {
    await deleteStatTemplate(row.id)
    ElMessage.success('删除成功')
    await loadTemplates()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '删除失败') }
}

onMounted(async () => {
  await Promise.all([loadAgencies(), loadNodes()])
  await Promise.all([loadDatasets(), loadTemplates()])
})
</script>

<style scoped>
.data-resource-page { min-height: 100vh; background: #f0f2f5; padding: 24px; }
.page-header { margin-bottom: 24px; }
.title-area h1 { font-size: 24px; font-weight: 600; margin: 0 0 8px 0; }
.title-area p { color: #666; margin: 0; }
.table-card { background: #fff; }
.toolbar { margin-bottom: 16px; }
.pagination-wrapper { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
