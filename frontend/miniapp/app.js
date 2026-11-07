App({globalData:{baseUrl:''},onLaunch(){this.globalData.baseUrl=wx.getStorageSync('ktvServer')||'';}});
