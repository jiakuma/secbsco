export type TaskType = 'statistic' | 'federated_learning'
export type ScenarioCode = 'infectious_spatiotemporal_prediction'

export const TASK_TYPE = {
  STATISTIC: 'statistic' as TaskType,
  FEDERATED_LEARNING: 'federated_learning' as TaskType,
}

export const SCENARIO_CODE = {
  T2_INFECTIOUS_SPATIOTEMPORAL_PREDICTION: 'infectious_spatiotemporal_prediction' as ScenarioCode,
}

export const TASK_TYPE_OPTIONS = [
  { label: '联合统计', value: TASK_TYPE.STATISTIC },
  { label: '联邦学习', value: TASK_TYPE.FEDERATED_LEARNING },
]

export const TASK_SCENARIO_OPTIONS = [
  {
    label: 'T2：跨区县传染病时空预测与疫情溯源',
    value: SCENARIO_CODE.T2_INFECTIOUS_SPATIOTEMPORAL_PREDICTION,
    task_type: TASK_TYPE.FEDERATED_LEARNING,
  },
]

export const T2_SCENARIO_PARAMS = {
  task_type: TASK_TYPE.FEDERATED_LEARNING,
  scenario_code: SCENARIO_CODE.T2_INFECTIOUS_SPATIOTEMPORAL_PREDICTION,
  scenario_name: '跨区县传染病时空预测与疫情溯源',
  federated_mode: 'horizontal',
  algorithm_type: 'prediction',
  model_type: 'mock_spatiotemporal_model',
  framework: 'mock',
  dataset_config: {
    main_table: 'IDSR_INDIVIDUAL_DIS',
    id_column: 'case_id_hash',
    feature_columns: [
      'disease_code',
      'onset_date',
      'diagnosis_date',
      'spatial_grid_id',
      'age_group',
      'gender',
      'occupation_code',
    ],
    label_column: 'risk_label',
  },
  train_config: {
    epochs: 5,
    batch_size: 32,
    learning_rate: 0.01,
  },
  privacy_config: {
    raw_data_export: false,
    secure_aggregation: true,
    blockchain_audit: true,
  },
  trace_config: {
    enabled: true,
    trace_table: 'SPATIOTEMPORAL_TRACE',
    intersection_field: 'spatial_grid_14d',
    trace_method: 'private_intersection',
  },
}

export const DEFAULT_STATISTIC_FIELD_MAPPING_TEXT = `{
  "patient_id": "patient_id",
  "positive": "positive"
}`

export const T2_FIELD_MAPPING_TEXT = `{
  "data_role": "t2_training_node",
  "local_table": "IDSR_INDIVIDUAL_DIS",
  "sample_desc": "本地区县脱敏传染病个案数据",
  "id_column": "case_id_hash",
  "label_column": "risk_label",
  "field_mapping": {
    "case_id_hash": "case_id_hash",
    "disease_code": "disease_code",
    "onset_date": "onset_date",
    "diagnosis_date": "diagnosis_date",
    "spatial_grid_id": "spatial_grid_id",
    "age_group": "age_group",
    "gender": "gender",
    "occupation_code": "occupation_code"
  }
}`

const FIELD_DESC_MAP: Record<string, string> = {
  disease_code: '疾病 ICD 编码，用于区分流感等传染病类型',
  onset_date: '发病日期，用于构建时间序列特征',
  diagnosis_date: '诊断日期，用于校正病例确认时间',
  spatial_grid_id: '脱敏后的空间网格编码，用于空间传播建模',
  age_group: '年龄分组，用于人群风险分层',
  gender: '性别，用于基础人群特征建模',
  occupation_code: '职业编码，用于识别学生、医务等风险群体',
}

export function parseJsonValue(value: any) {
  if (!value) return {}

  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch {
      return {}
    }
  }

  if (typeof value === 'object') return value

  return {}
}

export function buildTaskParamsJson(taskType: TaskType, scenarioCode?: ScenarioCode) {
  if (
    taskType === TASK_TYPE.FEDERATED_LEARNING &&
    (!scenarioCode || scenarioCode === SCENARIO_CODE.T2_INFECTIOUS_SPATIOTEMPORAL_PREDICTION)
  ) {
    return JSON.parse(JSON.stringify(T2_SCENARIO_PARAMS))
  }

  return {
    task_type: TASK_TYPE.STATISTIC,
  }
}

export function getTaskTypeFromRow(row: any): TaskType {
  const paramsJson = parseJsonValue(row?.params_json)
  return (row?.task_type || paramsJson.task_type || TASK_TYPE.STATISTIC) as TaskType
}

export function getTaskTypeTextFromRow(row: any) {
  const map: Record<TaskType, string> = {
    statistic: '联合统计',
    federated_learning: '联邦学习',
  }

  return map[getTaskTypeFromRow(row)] || '联合统计'
}

export function getTaskTypeTagTypeFromRow(row: any) {
  return getTaskTypeFromRow(row) === TASK_TYPE.FEDERATED_LEARNING ? 'warning' : 'success'
}

export function isFederatedLearningTask(row: any) {
  return getTaskTypeFromRow(row) === TASK_TYPE.FEDERATED_LEARNING
}

export function getTaskScenarioCodeFromRow(row: any) {
  const paramsJson = parseJsonValue(row?.params_json)
  return paramsJson.scenario_code || ''
}

export function getTaskScenarioTextFromRow(row: any) {
  const paramsJson = parseJsonValue(row?.params_json)
  if (!isFederatedLearningTask(row)) return '-'
  return paramsJson.scenario_name || '跨区县传染病时空预测与疫情溯源'
}

export function getFederatedModeText(value: string) {
  const map: Record<string, string> = {
    horizontal: '横向联邦学习',
    vertical: '纵向联邦学习',
  }
  return map[value] || value || '-'
}

export function getAlgorithmTypeText(value: string) {
  const map: Record<string, string> = {
    prediction: '时空预测',
    classification: '分类',
    regression: '回归',
  }
  return map[value] || value || '-'
}

export function getModelTypeText(value: string) {
  const map: Record<string, string> = {
    mock_spatiotemporal_model: 'Mock 时空预测模型',
    logistic_regression: '逻辑回归',
    linear_regression: '线性回归',
  }
  return map[value] || value || '-'
}

export function getFlDatasetFieldRows(paramsJson: any) {
  const params = parseJsonValue(paramsJson)
  const datasetConfig = params.dataset_config || {}
  const traceConfig = params.trace_config || {}
  const fields = Array.isArray(datasetConfig.feature_columns) && datasetConfig.feature_columns.length
    ? datasetConfig.feature_columns
    : T2_SCENARIO_PARAMS.dataset_config.feature_columns

  const rows = fields.map((field: string) => ({
    field,
    source: datasetConfig.main_table || T2_SCENARIO_PARAMS.dataset_config.main_table,
    desc: FIELD_DESC_MAP[field] || '联邦学习特征字段',
  }))

  rows.unshift({
    field: datasetConfig.id_column || T2_SCENARIO_PARAMS.dataset_config.id_column,
    source: datasetConfig.main_table || T2_SCENARIO_PARAMS.dataset_config.main_table,
    desc: '个案唯一脱敏标识，仅用于本地样本对齐和训练记录关联',
  })

  if (traceConfig.enabled) {
    rows.push({
      field: traceConfig.intersection_field || T2_SCENARIO_PARAMS.trace_config.intersection_field,
      source: traceConfig.trace_table || T2_SCENARIO_PARAMS.trace_config.trace_table,
      desc: '发病前 14 天到访空间网格集合，用于隐私求交溯源',
    })
  }

  return rows
}

export function getFlProcessSteps(paramsJson: any) {
  const params = parseJsonValue(paramsJson)
  const datasetConfig = params.dataset_config || {}
  const trainConfig = params.train_config || {}
  const traceConfig = params.trace_config || {}

  return [
    {
      title: '本地数据准备',
      desc: `各参与节点基于 ${datasetConfig.main_table || T2_SCENARIO_PARAMS.dataset_config.main_table} 准备脱敏个案特征，不上传原始数据。`,
    },
    {
      title: '横向联邦训练',
      desc: '各区县节点在本地训练时空预测模型，仅提交模型参数或梯度摘要。',
    },
    {
      title: '中心安全聚合',
      desc: `聚合服务按 ${trainConfig.epochs ?? T2_SCENARIO_PARAMS.train_config.epochs} 轮进行模型聚合，形成全局预测模型。`,
    },
    {
      title: '隐私求交溯源',
      desc: `基于 ${traceConfig.intersection_field || T2_SCENARIO_PARAMS.trace_config.intersection_field} 预留跨区县高频风险网格交集分析。`,
    },
    {
      title: '审计与存证',
      desc: '训练过程、参与方、模型摘要和结果摘要后续进入审计日志与链上存证。',
    },
  ]
}

export function buildDefaultPartyRole(task: any) {
  return isFederatedLearningTask(task) ? 'training_client' : 'data_provider'
}

export function buildDefaultFieldMappingText(task: any) {
  return isFederatedLearningTask(task) ? T2_FIELD_MAPPING_TEXT : DEFAULT_STATISTIC_FIELD_MAPPING_TEXT
}

export function getPartyFieldMapping(row: any) {
  return parseJsonValue(row?.field_mapping_json)
}

export function getPartyLocalTable(row: any) {
  const mapping = getPartyFieldMapping(row)
  return mapping.local_table || T2_SCENARIO_PARAMS.dataset_config.main_table
}

export function getPartySampleDesc(row: any) {
  const mapping = getPartyFieldMapping(row)
  return mapping.sample_desc || '本地任务数据资源'
}

export function getPartyFieldCount(row: any) {
  const mapping = getPartyFieldMapping(row)
  const fieldMapping = mapping.field_mapping || mapping
  if (!fieldMapping || typeof fieldMapping !== 'object') return 0
  return Object.keys(fieldMapping).length
}
