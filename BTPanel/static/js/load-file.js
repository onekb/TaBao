
; (function () { 
	
	// Description: 预加载文件
	var loadResource = [/** injection-load-file */]
	
	// Description: 已加载的资源
	var loadSession = JSON.parse(sessionStorage.getItem('load')) || []

	var xhr = new XMLHttpRequest() // 创建XMLHttpRequest对象


	/**
	 * @description 设置 load 内容
	 * @param {string} str 设置加载内容
	 */
	function setLoadContent(str) {
		loadSession.push(str)
		sessionStorage.setItem('load', JSON.stringify(loadSession))
	}

	/**
	 * @description 检查dom是否已经加载
	 * @param {string} str 
	 * @returns {boolean}
	 */
	function checkLoadContent(str) {
		return loadSession.includes(str)
	}


	/**
	 * @description 检查是否开始请求
	 * @returns {boolean}
	 */
	function checkLogin() {
		// 获取token，检查是否开始请求登录
		var token = sessionStorage.getItem('sendXhr');
		// 将token 初始化
		sessionStorage.setItem('sendXhr', '0');
		return token === '1';
	}

	// 递归请求
	function apiSend(index, urls) {
		if (index >= urls.length - 1) {
		} else {
			var isLoad = checkLoadContent(urls[index]) // 检查是否已经加载
			var isSend = checkLogin() // 检查是否开始其他请求
			if (isSend) return // 如果开始其他请求，终止当前请求
			if (!isLoad) {
				// 设置请求方法和URL，true表示异步
				xhr.open('GET', urls[index] + '?v=1780568589', true)
				// 发送请求
				xhr.send()
				// 监听onreadystatechange事件，当请求的状态发生变化时触发
				xhr.onreadystatechange = function () {
					// 当请求完成且成功时（readyState为4，status为200）
					if (xhr.readyState === 4 && xhr.status === 200) {
						// 存入SessionStorage
						setLoadContent(urls[index])
						// 继续下一条数据
						apiSend(index + 1, urls)
					}
				}
			} else {
				// 继续下一条数据
				apiSend(index + 1, urls)
			}
		}
	}

	// // 初始化预加载
	function preloadInit(urlList) {
		var loadedScripts = JSON.parse(sessionStorage.getItem('loadedScripts') || '[]')
		var urls = urlList.filter(url => !loadedScripts.includes(url))
		apiSend(0, urls)
	}

	// 预加载初始化
	window.onload = function () {
		// 如果当前环境是HTTPS则不进行预加载请求
		if (window.location.protocol === 'https:') {
			return
		}
		preloadInit(loadResource)
	}

})()
