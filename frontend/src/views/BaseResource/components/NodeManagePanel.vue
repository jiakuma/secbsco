<template>
  <div class="manage-panel">
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="节点编码 / 节点名称" clearable style="width: 230px" @keyup.enter="loadList" />
        </el-form-item>
        <el-form-item label="所属机构">
          <el-cascader v-model="searchForm.agency_path" :options="agencyTreeOptions" :props="{value:'id',label:'agency_name',children:'children',checkStrictly:true,emitPath:false,expandTrigger:'hover'}" filterable clearable placeholder="全部机构" style="width: 220px" @visible-change="handleCascaderVisibleChange" />
        </el-form-item>
        <el-form-item label="节点类型">
          <el-select v-model="searchForm.node_type" clearable placeholder="全部" style="width: 150px">
            <el-option label="服务节点" value="service_node" />
            <el-option label="数据节点" value="data_node" />
            <el-option label="计算节点" value="compute_node" />
            <el-option label="区块链节点" value="blockchain_node" />
            <el-option label="网关节点" value="gateway_node" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" clearable placeholder="全部" style="width: 130px">
            <el-option label="已注册" value="registered" />
            <el-option label="启用" value="active" />
            <el-option label="离线" value="offline" />
            <el-option label="停用" value="disabled" />
            <el-option label="异常" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
          <el-button type="success" @click="openCreateDialog">新增节点</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="nodeList" stripe border v-loading="loading" style="width: 100%">
        <el-table-column prop="node_name" label="节点名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="node_code" label="节点编码" min-width="180" show-overflow-tooltip />
        <el-table-column prop="agency_name" label="所属机构" min-width="170" show-overflow-tooltip />
        <el-table-column prop="node_type" label="类型" width="120"><template #default="{ row }">{{ nodeTypeText(row.node_type) }}</template></el-table-column>
        <el-table-column prop="endpoint" label="访问地址" min-width="220" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" align="center"><template #default="{ row }"><el-tag :type="statusTagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag></template></el-table-column>
        <el-table-column prop="last_heartbeat_at" label="最近心跳" min-width="160" show-overflow-tooltip><template #default="{ row }">{{ row.last_heartbeat_at || '-' }}</template></el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="row.status !== 'active'" link type="success" @click="handleEnable(row)">启用</el-button>
            <el-button v-else link type="warning" @click="handleDisable(row)">停用</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <span class="total-text">Total {{ total }}</span>
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50]" layout="sizes, prev, pager, next, jumper" @current-change="loadList" @size-change="loadList" />
      </div>
    </el-card>

    <el-dialog v-model="formDialogVisible" :title="formMode === 'create' ? '新增节点' : '编辑节点'" width="760px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="节点编码" prop="node_code"><el-input v-model="form.node_code" :disabled="formMode === 'edit'" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="节点名称" prop="node_name"><el-input v-model="form.node_name" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="所属机构" prop="agency_id"><el-cascader v-model="form.agency_id" :options="agencyTreeOptions" :props="{value:'id',label:'agency_name',children:'children',checkStrictly:true,emitPath:false}" filterable style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="节点类型" prop="node_type"><el-select v-model="form.node_type" style="width:100%"><el-option label="服务节点" value="service_node" /><el-option label="数据节点" value="data_node" /><el-option label="计算节点" value="compute_node" /><el-option label="区块链节点" value="blockchain_node" /><el-option label="网关节点" value="gateway_node" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="访问地址"><el-input v-model="form.endpoint" placeholder="如 http://192.168.0.40:18180" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="服务URL"><el-input v-model="form.service_url" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="健康检查URL"><el-input v-model="form.health_check_url" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="Ray地址"><el-input v-model="form.ray_address" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="存证服务URL"><el-input v-model="form.anchor_service_url" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="formDialogVisible=false">取消</el-button><el-button type="primary" :loading="submitLoading" @click="submitForm">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="节点详情" width="720px">
      <el-descriptions v-if="detail" :column="2" border>
        <el-descriptions-item label="节点名称">{{ detail.node_name }}</el-descriptions-item>
        <el-descriptions-item label="节点编码">{{ detail.node_code }}</el-descriptions-item>
        <el-descriptions-item label="所属机构">{{ detail.agency_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="节点类型">{{ nodeTypeText(detail.node_type) }}</el-descriptions-item>
        <el-descriptions-item label="访问地址" :span="2">{{ detail.endpoint || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="最近心跳">{{ detail.last_heartbeat_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ detail.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { getAgencyTree } from '@/api/agency'
import { createNode, disableNode, enableNode, getNodeDetail, getNodeList, updateNode } from '@/api/node'

const emit = defineEmits<{ (e: 'summary-change', payload: { total: number; active: number }): void }>()
const loading = ref(false); const submitLoading = ref(false)
const nodeList = ref<any[]>([]); const agencyTreeOptions = ref<any[]>([])
const total = ref(0); const page = ref(1); const pageSize = ref(10)
const formDialogVisible = ref(false); const detailVisible = ref(false)
const formMode = ref<'create'|'edit'>('create'); const editingId = ref<number|null>(null); const detail = ref<any>(null)
const formRef = ref<FormInstance>()
const searchForm = reactive<any>({ keyword:'', agency_path:undefined, status:'', node_type:'' })
const form = reactive<any>({})
const formRules: FormRules = { node_code:[{required:true,message:'请输入节点编码',trigger:'blur'}], node_name:[{required:true,message:'请输入节点名称',trigger:'blur'}], agency_id:[{required:true,message:'请选择所属机构',trigger:'change'}], node_type:[{required:true,message:'请选择节点类型',trigger:'change'}] }
function unwrap(res:any){ return res?.data ?? res }
function resetForm(){ Object.keys(form).forEach(k=>delete form[k]); Object.assign(form,{node_code:'',node_name:'',agency_id:null,node_type:'compute_node',endpoint:'',service_url:'',health_check_url:'',ray_address:'',anchor_service_url:'',description:'',status:'active'}) }
async function loadAgencyTree(){ const res:any=await getAgencyTree(); agencyTreeOptions.value=unwrap(res)||[] }
async function loadList(){ loading.value=true; try{ const params:any={...searchForm,page:page.value,page_size:pageSize.value}; if(searchForm.agency_path) params.agency_id=searchForm.agency_path; const res:any=await getNodeList(params); const data=unwrap(res); nodeList.value=data.items||[]; total.value=data.total||0; emit('summary-change',{total:total.value,active:nodeList.value.filter(n=>n.status==='active').length}) } finally{ loading.value=false } }
function handleSearch(){ page.value=1; loadList() }
function resetSearch(){ Object.assign(searchForm,{keyword:'',agency_path:undefined,status:'',node_type:''}); handleSearch() }
function openCreateDialog(){ formMode.value='create'; editingId.value=null; resetForm(); formDialogVisible.value=true }
function openEditDialog(row:any){ formMode.value='edit'; editingId.value=row.id; resetForm(); Object.assign(form,row); formDialogVisible.value=true }
async function submitForm(){ await formRef.value?.validate(); submitLoading.value=true; try{ const payload={...form}; if(formMode.value==='create') await createNode(payload); else if(editingId.value) await updateNode(editingId.value,payload); ElMessage.success('保存成功'); formDialogVisible.value=false; await loadList() } finally{ submitLoading.value=false } }
async function openDetail(row:any){ const res:any=await getNodeDetail(row.id); detail.value=unwrap(res); detailVisible.value=true }
async function handleEnable(row:any){ await enableNode(row.id); ElMessage.success('已启用'); await loadList() }
async function handleDisable(row:any){ await ElMessageBox.confirm(`确认停用节点「${row.node_name}」？`,'提示',{type:'warning'}); await disableNode(row.id); ElMessage.success('已停用'); await loadList() }
async function handleDelete(row:any){
  await ElMessageBox.confirm(`确认物理删除节点「${row.node_name}」？该节点的群组授权关系将一并删除。`,'删除确认',{type:'warning'})
  const nodeApi:any = await import('@/api/node')
  if (typeof nodeApi.deleteNode !== 'function') {
    ElMessage.error('前端接口文件 src/api/node.ts 缺少 deleteNode 方法，请先补充该方法')
    throw new Error('src/api/node.ts missing deleteNode export')
  }
  await nodeApi.deleteNode(row.id)
  ElMessage.success('已删除')
  await loadList()
}
function nodeTypeText(v:string){ return ({service_node:'服务节点',data_node:'数据节点',compute_node:'计算节点',blockchain_node:'区块链节点',gateway_node:'网关节点'} as any)[v]||v||'-' }
function statusText(v:string){ return ({registered:'已注册',checking:'检查中',active:'启用',offline:'离线',disabled:'停用',failed:'异常'} as any)[v]||v||'-' }
function statusTagType(v:string):'success'|'info'|'warning'|'danger'{ return v==='active'?'success':v==='failed'?'danger':v==='disabled'?'info':'warning' }
function handleCascaderVisibleChange(visible:boolean){ if(visible) searchForm.agency_path=undefined }
onMounted(async()=>{ await loadAgencyTree(); await loadList() })
</script>

<style scoped>
.manage-panel{padding-top:8px}.filter-card{margin-bottom:12px;border-radius:12px}.pagination{display:flex;align-items:center;justify-content:space-between;margin-top:14px}.total-text{color:#64748b;font-size:13px}
</style>
