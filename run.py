#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time	: 2017/8/25 21:59
# @Author  : Nikan
# @File	: run.py



from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
import hashlib
import queue
import time

import base64
from PIL import Image
from io import BytesIO
import requests

# def robust(func):
# 	def add_robust(*args, **kwargs):
# 		while 1:
# 			try:
# 				return func(*args, **kwargs)
# 			except Exception as e:
# 				print("error", e)
# 				traceback.print_exc()
# 	return add_robust

def get_expanded_scientific_notation(flt):
	str_vals = str(flt).split('e')
	coef = float(str_vals[0])
	exp = int(str_vals[1])
	return_val = ''
	if int(exp) > 0:
		return_val += str(coef).replace('.', '')
		return_val += ''.join(['0' for _ in range(0, abs(exp - len(str(coef).split('.')[1])))])
	elif int(exp) < 0:
		return_val += '0.'
		return_val += ''.join(['0' for _ in range(0, abs(exp) - 1)])
		return_val += str(coef).replace('.', '')
	return return_val

class BiAn():
	def __init__(self, username=None, passw=None, **kwargs):

		self.username = username
		self.passw = passw
		self.session = requests.session()
		self.host = "https://www.binance.com/"
		self.driver = webdriver.PhantomJS(executable_path="phantomjs/bin/phantomjs.exe")
		self.cookies = {}
		self.csrf = None
		self.project_id = "-1"
		self.buy_num = "-1"
		self.price = 1
		self.interval = 2
		if kwargs:
			if kwargs.get('username'):
				self.username = kwargs.get('username')
			if kwargs.get('password'):
				self.passw = kwargs.get('password')
			self.project_id = kwargs.get('ID', "-1")
			self.buy_num = kwargs.get('buy_num', "-1")
			self.interval = int(kwargs.get('interval', 2))
	def before_login(self):
		pass

	def check_captcha(self,driver):
		while 1:
			element_image = driver.find_element_by_xpath('//*[@id="nc_1__imgCaptcha_img"]/img')
			image_src = element_image.get_attribute("src")
			image_data = image_src.split(',')[1]
			t = base64.b64decode(image_data)
			image = Image.open(BytesIO(t))
			image.show()
			recog = input("请输入验证码：")
			input2 = driver.find_element_by_xpath('//*[@id="nc_1_captcha_input"]')
			input2.send_keys(recog)
			input2.send_keys(Keys.ENTER)
			time.sleep(1)
			captcha_error = driver.find_element_by_xpath('//*[@id="nc_1__scale_text"]/span')
			if captcha_error.text == 'Please input verification code':
				print('验证失败...')
				continue
			else:
				print('验证成功...')
				return 1

	def login(self):
		# 利用浏览器进行登录
		self.driver.get("https://www.binance.com/login.html")
		# 输入框中填入值
		element_username = self.driver.find_element_by_id('email')
		element_passw = self.driver.find_element_by_id('pwd')
		element_username.send_keys(self.username)
		element_passw.send_keys(self.passw)

		# 控制滑块拖动
		action_chains = ActionChains(self.driver)
		element_btn = self.driver.find_element_by_xpath('//*[@id="nc_1_n1z"]')
		action_chains.click_and_hold(on_element=element_btn)
		action_chains.move_by_offset(400, 0)
		action_chains.perform()
		element_error = self.driver.find_element_by_xpath('//*[@id="nc_1__scale_text"]')

		while 1:
			if element_error.text == "Please input verification code":
				# 验证验证码的正确性
				self.check_captcha(self.driver)
				submit = self.driver.find_element_by_id("login-btn")
				submit.send_keys(Keys.ENTER)
				break
			else:
				pass

		time.sleep(3)
		print("登录成功...")
		cookies = dict()
		for cookie in self.driver.get_cookies():
			cookies[cookie['name']] = cookie['value']
		self.cookies = cookies
		self.driver.quit()

	def showDetail(self):
		#显示最大购买量
		print("正在查询产品的详细信息...")
		project_detail = self.get_project_detail()
		price = project_detail['price']
		if price == '待定':
			self.price = "待定"
		else:
			self.price = get_expanded_scientific_notation(price)
		print("项目名称：", project_detail.get("projectName"))
		print(" 项目状态：", project_detail.get("projectStatusName"))
		print("是否可买：", "否" if project_detail.get("purchase") == False else "是")
		print("抢购价格：     1{symbol} = {price} {asset}".format(symbol=project_detail['symbol'], price=self.price, asset=project_detail['asset']))
		print("发行数量：      {}".format(project_detail['distributeNum']))
		print("-------------------------------------")
		print("您目前最多可以购买：", self.get_max_purchase(), "份")
		print()

	def get_project_detail(self):
		url = "https://www.binance.com/project/getProject.html"
		params = {
			"projectId": self.project_id
		}
		csrf = self.cookies['CSRFToken'].encode()
		x = hashlib.md5()
		x.update(csrf)
		self.csrf = x.hexdigest()
		headers = {
			"CSRFToken": self.csrf
		}
		self.session.headers.update(headers)
		cj = requests.utils.cookiejar_from_dict(self.cookies)
		self.session.cookies = cj

		r = self.session.post(url, params=params)

		r.raise_for_status()
		return r.json()

	def get_max_purchase(self):
		url = "https://www.binance.com/project/maxPurchase.html"
		params = {
			"projectId": self.project_id
		}

		r = self.session.post(url, params=params)

		r.raise_for_status()
		return r.json()["max"]

	def purchase(self):
		purchase_uri = "https://www.binance.com/project/purchase.html"

		params = {
			"projectId":self.project_id,
			"num": self.buy_num,
			"price": self.price
		}

		while True:
			try:
				print("当前时间：" + time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
				r =self.session.post(purchase_uri, params=params)
				ret = r.json()

				if ret['success'] is True:
					print("成功购买，等待确认结果...")
					get_purchase_status_url = "https://www.binance.com/project/getPurchaseStatus.html?id=" + ret.get('id')
					while True:
						r = self.session.get(get_purchase_status_url)
						result = r.json().get('status')
						if result == 0 or '0':
							print("没有结果")
						elif result == 1 or '1':
							print("成功购买")
							return 1
						elif result == 2 or '2':
							print("购买失败")
							self.retry_purchase()
				elif ret['success'] is False:
					print("购买失败，原因：{}".format(ret['desc']))
					print(ret['desc'])
				time.sleep(self.interval)
			except:
				pass


	def run(self):
		print("用户名：",self.username, "密码：", self.passw)
		self.login()
		if self.project_id == '-1':
			self.project_id = input("请输入抢购产品的ID：")
		print("产品ID为：" + self.project_id)
		self.showDetail()
		if self.buy_num == '-1':
			self.buy_num = input("请输入要购买的数量（请不要超过您目前最多可以购买的数量）：")
		print("购买数量为：" + self.buy_num)
		print("开始监控并尝试进行抢购...间隔为" + str(self.interval) + '秒')
		self.purchase()
		return

	def retry_purchase(self):
		print("尝试重新购买...")
		self.purchase()

if __name__ == '__main__':
	with open("配置.txt", "r", encoding="utf-8-sig") as f:
		info = f.read().splitlines()
		info_dict = {}
		for i in info:
			a, b = i.split("：")
			info_dict[a] = b
		print(info_dict)
	user = None
	passw = None
	if not info_dict.get('username'):
		user = input("输入账号名：")
	if not info_dict.get('password'):
		passw = input("输入密码：")
	try:
		bi = BiAn(**info_dict)
		bi.run()
	except Exception as e:
		print(e)
		print("操作错误")
		print("请手动关闭窗口...")




