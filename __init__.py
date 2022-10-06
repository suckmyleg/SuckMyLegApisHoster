import json
from urllib.request import urlopen
import requests
from threading import Thread
from pickle import loads, dumps
import urllib.parse
import socket
import linecache
import sys

VERSION = "0.2.4"

def PrintException():
	exc_type, exc_obj, tb = sys.exc_info()
	f = tb.tb_frame
	lineno = tb.tb_lineno
	filename = f.f_code.co_filename
	linecache.checkcache(filename)
	line = linecache.getline(filename, lineno, f.f_globals)
	print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))

# TEXTS

class Clean:
	def __init__(self, fun):
		self.fun = fun
		self.id = b"0"

	def run(self, s, data):
		for g in ["c"]:
			del data[g]

		output = (self.fun(s, data), self.id)
		###print("Clean", output)
		return output


# JSON (LISTS, DIRS)

class Dumper:
	def __init__(self, fun):
		self.fun = fun
		self.id = b"1"

	def run(self, s, data):
		output = (json.dumps(self.fun(s, data)), self.id)
		###print("Dumper", output)
		return output


# BYTES (IMAGES, ETC)

class Byter:
	def __init__(self, fun):
		self.fun = fun
		self.id = b"2"

	def run(self, s, data):
		output = (self.fun(s, data), self.id)
		return output

class Commands:
	def __init__(self, server):
		self.server = server
		self.commands = ["hoster_version", "connect"]

	def command_connect(self, s, data):
		conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		addr = data["sockname"]
		conn.connect(addr)
		s = Thread(target=self.server.on_connection, args=(conn, addr))
		s.start()
		return "True", b"0"

	def command_help(self, s, data):
		return self.commands, b"1"

	def command_hoster_version(self, s, data):
		return VERSION, b"0"

	def command_stop(self, s, data):
		self.server.server_status = False
		self.server.server.shutdown(socket.SHUT_RDWR)
		self.server.server.close()
		return "Closed", b"0"

class Bridge:
	def __init__(self, host=False, port=False, location=False, url=False):
		self.host = host
		self.port = port
		self.location = location
		self.url = url

	def get_clients(self, n):
		requests.get("{}:{}/Apis/Main/?c=get_clients&loc={}".format(self.host, self.port, self.location))


class tools:
	def __init__(self, port, host="localhost"):
		self.server_status = True
		self.host = host
		self.port = port
		self.server = False
		self.delay = 0.5
		self.commands = Commands(self)

	def start(self):
		self.start_connection()
		self.start_server()

	def add_attr(self, name, module):
		setattr(self.commands, name, module)

	def add_command(self, name, fun, clean=True, dump=False, byte=False):
		if byte:
			print(f"SETTING COMMAND name:{name} type:byte")
			Function = Byter(fun).run
		else:
			if dump:
				print(f"SETTING COMMAND name:{name} type:dump")
				Function = Dumper(fun).run
			else:
				print(f"SETTING COMMAND name:{name} type:clean")
				Function = Clean(fun).run
		
		setattr(self.commands, f"command_{name}", Function)
		self.commands.commands.append(name)

	def start_connection(self):
		print("Binding server")
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.bind((self.host, self.port))
		print("Binded")

	def on_connection(self, conn, addr):
		print("New connection =>", addr)
		while True:
			try:
				argvs = loads(conn.recv(8024))
				#print(argvs)
				out, i = self.react(argvs)
				if not i == b"2":
					out = dumps(out)
				result = out + b"%SEPARATOR@" + i
				conn.sendall(dumps(len(result)))
				###print(result)
				conn.sendall(result)
			except Exception as e:
				print("Lost connection =>", addr, f"({e})")
				break
		exit()

	def main_console(self):
		while self.server_status:
			c = input("command: ")

			p = input("  ├ key: ")

			data = {"c":c}

			while p != "":
				data[p] = input("  ├ value: ")
				p = input("  ├\n  ├ key: ")

			out, i = self.react(data)

			if i == b"2":
				out = loads(out)

			###print(out)

	def recv_clients(self):
		self.server.listen()
		print("Listening to clients")
		while self.server_status:
			conn, addr = self.server.accept()
			Thread(target=self.on_connection, args=(conn, addr)).start()
		exit()

	def start_server(self):
		print("Starting server")
		Thread(target=self.recv_clients).start()
		Thread(target=self.main_console).start()
		return True

	def clear_garbage(self, data):
		for g in ["c"]:
			del data[g]

		return data

	def react(self, args):
		try:
			fun = getattr(self.commands, f"command_{args['c']}")
		except:
			return f"Uknown command {args['c']}", b"0"
		else:

			try:
				#print(f"Calling command_{args['c']}(self, {args})", end="", flush=False)
				r, i = fun(self.commands, args)
				###print(f"Returned {r}, {i}")
			except Exception as e:
				PrintException()
				message = f"||  Error {e} ||"
				lines = "-"*len(message)
				###print(f"\n{lines}\n{message}\n{lines}")
				return str(e), b"0"
			else:
				#print(" Ok")
				return r, i
