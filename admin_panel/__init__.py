# ceneris/__init__.py
try:
	import pymysql
except ModuleNotFoundError:
	# Si PyMySQL no está instalado, Django puede usar mysqlclient (MySQLdb)
	pass
else:
	# Le decimos a pymysql que actúe como si fuera MySQLdb (la librería que usa Django)
	pymysql.install_as_MySQLdb()