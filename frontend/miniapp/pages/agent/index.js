const {request,download}=require('../../utils/api');
const ui=require('../../utils/ui');
Page({
  data:{question:'统计本月消费最高的房间，并找出金额异常的账单',modes:['规则查询（不调用大模型）','本机 Ollama 模型规划'],modeIndex:0,busy:false,error:'',result:null,history:[],reportFile:''},
  onShow(){this.refresh();},
  input(e){this.setData({question:e.detail.value});},
  mode(e){this.setData({modeIndex:Number(e.detail.value)});},
  refresh(){return ui.safe(this,async()=>{this.setData({history:await request('/agent/runs')});});},
  ask(){return ui.safe(this,async()=>{
    if(!this.data.question.trim())throw Error('请输入查询问题');
    const result=await request('/agent/runs','POST',{question:this.data.question,mode:this.data.modeIndex?'ollama':'rules'});
    this.setData({result,reportFile:'',history:await request('/agent/runs')});
  });},
  open(e){return ui.safe(this,async()=>{this.setData({result:await request('/agent/runs/'+e.currentTarget.dataset.id),reportFile:''});});},
  retry(){return ui.safe(this,async()=>{
    this.setData({result:await request('/agent/runs/'+this.data.result.id+'/retry','POST'),history:await request('/agent/runs')});
  });},
  source(e){const source=this.data.result.sources[Number(e.currentTarget.dataset.index)];
    if(source.kind==='bill')ui.navigate('/pages/detail/index?bill_id='+source.id);
    else if(source.kind==='image')ui.navigate('/pages/detail/index?id='+source.id);
    else if(source.kind==='document')ui.safe(this,async()=>{const d=await request(source.url.replace('/api/v1',''));wx.showModal({title:'业务规则来源',content:d.text,showCancel:false});});
  },
  report(){return ui.safe(this,async()=>{
    const name='ktv-report-'+this.data.result.id+'.md';
    const reportFile=await download('/agent/runs/'+this.data.result.id+'/report',name);
    this.setData({reportFile,reportName:name});wx.showToast({title:'报告已下载',icon:'success'});
  });},
  saveReport(){return ui.safe(this,async()=>{
    if(!wx.shareFileMessage)throw Error('当前环境不支持文件菜单，请在微信真机操作');
    await new Promise((resolve,reject)=>wx.shareFileMessage({filePath:this.data.reportFile,fileName:this.data.reportName,success:resolve,fail:e=>/cancel/.test(e.errMsg)?resolve():reject(Error('无法打开文件菜单'))}));
  });}
});
