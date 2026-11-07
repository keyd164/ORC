const status={queued:'排队中',processing:'识别中',completed:'识别完成',failed:'识别失败',pending:'待复核',confirmed:'已复核',none:'无重复',suspected:'疑似重复',excluded:'已确认重复',corrected:'已修正',invalid:'已确认空值'};
const money=v=>v===null||v===undefined?'—':(v/100).toFixed(2);
function today(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function bill(b){return {...b,money:money(b.received_amount),reviewText:status[b.review_status]||b.review_status,duplicateText:status[b.duplicate_status]||b.duplicate_status};}
function image(i){return {...i,money:money(i.received_amount),statusText:status[i.status]||i.status};}
async function safe(page,fn){if(page.data.busy)return;page.setData({busy:true,error:''});try{return await fn();}catch(e){page.setData({error:e.message||'操作失败，请重试'});}finally{page.setData({busy:false});}}
function confirm(title,content){return new Promise(resolve=>wx.showModal({title,content,success:r=>resolve(r.confirm),fail:()=>resolve(false)}));}
function navigate(url){wx.navigateTo({url});}
module.exports={status,money,today,bill,image,safe,confirm,navigate};
