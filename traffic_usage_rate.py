import rrdtool
import json
import sys
import time

import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr

rrd_dir = '/opt/rra'
end_date = '00:00'
result = []
field_names = ["出口名字", "最大(G)", "利用率", "水平"]

if len(sys.argv) < 2 or sys.argv[1] == 'week':
	start_date = 'end-1w'
	step = '1800'
	desc = "上周(第%s周)" % (int(time.strftime("%W")) - 1)
elif sys.argv[1] == 'month':
	start_date = 'end-1m'
	step = '7200'
	desc = "上月(%s月份)" % (int(time.strftime("%m")) - 1)
else:
	print('set correct check range\nweek or month')
	sys.exit(0)

with open('%s/info.json' %sys.path[0], 'r') as f:
	ck = json.load(f)
with open('%s/head.html' %sys.path[0], 'r') as f:
	html_head = f.read()


def level_judgment(rate):
	if rate >= 95:
		level = '<font color="red"> 过高 </font>'
	elif rate <= 80:
		level = '<font color="dodgerblue"> 过低 </font>'
	else:
		level = "正常"
	return level


def _format_addr(s):
	name, addr = parseaddr(s)
	return formataddr((Header(name).encode(), addr))


def let_them_know(text, subject):
	email = '%s/email.json' % sys.path[0]
	with open(email, 'r', encoding='utf-8') as f:
		email_info = json.load(f)
	to_addr = email_info.get('to_addr')
	# 生成收件人列表
	email_list = ','.join(_format_addr('%s <%s>' % (k, v)) for k, v in to_addr.items())
	# 填写邮件内容
	msg = MIMEText(text, 'html', 'utf-8')
	msg['From'] = _format_addr('天津网管监控 <%s>' % email_info['from_addr'])
	msg['To'] = email_list
	msg['Subject'] = Header(subject).encode()
	# 发送邮件
	server = smtplib.SMTP(email_info['smtp_server'], 25)
	server.login(email_info['from_addr'], email_info['passwd'])
	server.sendmail(email_info['from_addr'], to_addr.values(), msg.as_string())
	server.quit()


def html_table(table_data,table_header):
	yield html_head
	yield '  <tr><th>'
	yield '    </th><th>'.join(table_header)
	yield '  </th></tr>'
	for td in table_data:
		yield '  <tr><td>'
		yield '    </td><td>'.join(td)
		yield '  </td></tr>'
	yield '</table>'


def create_rrd_cmd(id):
	rrd_cmd=[]
	rrd_cdef=[]
	for i,j in enumerate(id):
		rrd_cmd.append('DEF:data%s=%s/%s.rrd:traffic_in:AVERAGE' % (i, rrd_dir, j))
		rrd_cdef.append('data%s,+,' %i)
	rrd_cdef.insert(0, 'CDEF:mymax=0,')
	rrd_cdef.append('8,*,1000000000,/')
	rrd_cdef=''.join(rrd_cdef)
	rrd_cmd.append(rrd_cdef)
	return rrd_cmd


for i in ck.keys():
	rrd_id = ck[i][1]
	rrd_cmd = create_rrd_cmd(rrd_id)
	max_traffic = rrdtool.graph("x", "-e", end_date, "-s", start_date, "--step", step, rrd_cmd,"PRINT:mymax:MAX:%.2lf")
	rate = float(max_traffic[2][0]) / ck[i][2] * 100
	level = level_judgment(rate)
	result.append([ck[i][0], max_traffic[2][0], '%s%%' % round(rate, 1), level])

result = '\n'.join(html_table(sorted(result), field_names))

let_them_know(result, '%s出口使用率统计' % desc)
