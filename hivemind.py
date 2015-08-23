# yes its all in one file, deal with it

import random
import socket
import threading
import socks
import string
import os

def rand_string(length):
	return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def split_sender(sender):

	split_1 = sender.split("!")

	if len(split_1) == 2:
		split_2 = split_1[1].split("@")
		nick, user, host = split_1[0], split_2[0], split_2[1]
		return (nick, user, host)
	elif len(split_1) == 1:
		return ("", "", sender)
	else:
		return ("", "", "")

def random_line_color_id(length):

	#there's probably a better way to do this

	result = ""

	# this gets 1-10 as strings
	colors = range(1,10)
	for i in range(0, len(colors)):
		colors[i] = str(colors[i])

	for i in range(0, length):
		result = result + "\x03" + random.choice(colors)

	return result + "\x0F"

class IRCSkeleton:

	def __init__(self, proxy_host="127.0.0.1", proxy_port=7000):

		if proxy_host == "" or proxy_port < 0:
			self.socket = socket.socket()
		else:
			self.socket = socks.socksocket()
			self.socket.setproxy(socks.PROXY_TYPE_SOCKS5, proxy_host, proxy_port)

	#### IMPLEMENT THESE FUNCTIONS ####

	# this is gay polymorphism or whatever

	def on_bot_command(self, sender, channel, message, command, args):
		pass

	def on_connect(self):
		pass

	def on_join(self, sender, channel):
		pass

	def on_quit(self, sender, message):
		pass

	def on_part(self, sender, channel, message):
		pass

	def on_kick(self, sender, channel, message):
		pass

	#### BOILERPLATE ####

	def send_line(self, line):

		self.socket.send(line.strip() + "\n")

	def send_message(self, channel, message):

		self.send_line("PRIVMSG " + channel + " :" + message)

	def join(self, channel):

		self.send_line("JOIN " + channel)

	def connect(self, host, port):

		self.socket.connect((host, port))

		self.send_line("USER " + self.username + " " + self.username + " " + self.username + " :" + self.username)
		self.send_line("NICK " + self.nick)

		self.current_server_host = host
		self.current_server_port = port

	def on_ping(self, data):

		self.send_line("PONG " + data)

	def on_privmsg(self, sender, channel, message):

		if message.startswith("~"):
			message_split = message.split(" ", 1)

			command = message_split[0][1:]
			args = []
			if len(message_split) > 1:
				args = message_split[1].split(" ")

			self.on_bot_command(sender, channel, message, command, args)

	def on_irc_command(self, sender, command, data):

		if command == "001":
			self.on_connect()
		elif command == "PRIVMSG":
			split_data = data.split(" ", 1)
			channel, message = (split_data[0], split_data[1][1:])
			self.on_privmsg(sender, channel, message)
		elif command == "404":
			self.socket.close()
		elif command == "JOIN":
			split_data = data.split(" ")
			self.on_join(sender, split_data[0])
		elif command == "QUIT":
			self.on_quit(sender, data[1:])
		elif command == "PART":
			split_data = data.split(" ", 1)
			channel, message = (split_data[0], split_data[1][1:])
			self.on_part(sender, channel, message)
		elif command == "KICK":
			split_data = data.split(" ", 1)
			channel, message = (split_data[0], split_data[1][1:])
			self.on_kick(sender, channel, message)

	def on_line(self, line):

		split_line = line.split(" ")
		split_len = len(split_line)

		if split_len == 2:
			if split_line[0] == "PING":
				self.on_ping(split_line[1])
		elif line[:1] == ":" and split_len >= 2:
			split_line_3 = line.split(" ", 2)
			sender, command, data = (split_line_3[0][1:], split_line_3[1], split_line_3[2])
			sender = split_sender(sender)
			self.on_irc_command(sender, command, data)

	def bot_thread(self):

		asfile = self.socket.makefile()
		while True:
			line = asfile.readline().strip()
			if len(line) == 0:
				break
			self.on_line(line)

	def start_listen(self, threaded):

		if not threaded:
			self.bot_thread()
		elif self.listen_thread == None:
			self.listen_thread = threading.Thread(target=bot_thread, args=[self])
			self.listen_thread.start()
		else:
			raise Exception("Bot has already got a listen_thread")

class Herder(IRCSkeleton):

	def __init__(self, default_channel, proxy_host, proxy_port):

		IRCSkeleton.__init__(self, "", 0)

		self.default_channel = default_channel
		self.nick = "Mr_Herder" #rand_string(7)
		self.username = "Herder" #rand_string(7)

		self.loader = SlaveLoader(proxy_host, proxy_port)

	def on_connect(self):

		print("Herder is connected")
		self.join(self.default_channel)

	def on_bot_command(self, sender, channel, message, command, args):

		if command == "ascii":
			if len(args) == 1:
				if self.loader.has_slaves():
					ascii_file = args[0]
					script_path = os.path.dirname(os.path.realpath(__file__))
					ascii_path = os.path.normpath(os.path.realpath(script_path + "/ascii/" + args[0]))
					ascii_file_after_normalize = ascii_path.replace(script_path, "").replace("/ascii/", "")

					# lfi defense!!
					if ascii_file_after_normalize == ascii_file and os.path.isfile(ascii_path):
						self.loader.load_ascii(ascii_path)
					else:
						self.send_message(self.default_channel, "That's not a valid file name (doesn't exist)")
				else:
					self.send_message(self.default_channel, "No slaves are loaded")
			else:
				self.send_message(self.default_channel, "usage: ~ascii <ascii art file>")
		elif command == "slaves":
			if len(args) == 1:
				slave_num = 0
				try:
					slave_num = int(args[0])
				except: # yes this is bad im lazy
					pass

				if slave_num < 100 and slave_num > 0:
					for i in range(0, slave_num):

						host, port, channel = self.current_server_host, self.current_server_port, self.default_channel

						self.loader.create_slave(host, port, channel)
				else:
					self.send_message(self.default_channel, "That's way many slaves to load")
			else:
				self.send_message(self.default_channel, "usage: ~slaves <num to load>")

	def on_quit(self, sender, message):
		
		nick, user, host = sender

		if nick != self.nick:
			self.loader.remove_loaded_slave(nick)

	def on_part(self, sender, channel, message):

		nick, user, host = sender

		if nick != self.nick:
			self.loader.remove_loaded_slave(nick)

	def on_kick(self, sender, channel, message):
		
		nick, user, host = sender

		if nick != self.nick:
			self.loader.remove_loaded_slave(nick)

	def on_join(self, sender, channel):
		
		nick, user, host = sender

		if nick != self.nick:
			self.loader.add_loaded_slave(nick)

	def on_privmsg(self, sender, channel, message):

		IRCSkeleton.on_privmsg(self, sender, channel, message) #super class on_privmsg
		self.loader.check_id_and_use(message)

class SlaveLoader:

	def __init__(self, proxy_host, proxy_port):

		self.proxy_host = proxy_host
		self.proxy_port = proxy_port
		self.slave_nick_prefix = "aS"

		self.id_length = 5
		self.use_first_n_bots = 15

		self.loaded_slaves = []
		self.slave_objects = {}

		self.current_slave = 0
		self.current_ascii = ""
		self.current_ascii_line = 0
		self.current_ascii_line_id = ""

	def load_ascii(self, ascii_path):

		self.current_ascii = open(ascii_path).readlines()
		self.current_ascii_line = 0
		self.current_ascii_line_id = ""
		self.use_slave()

	def check_id_and_use(self, message):

		# if we see a message with the correct identifier
		# then increment the line number and send the next line

		if len(message) > self.id_length:

			# identifier length (2 bytes/color code) + 1 reset char
			actual_length = self.id_length * 2 + 1
			this_id = message[:actual_length]
			if this_id == self.current_ascii_line_id:
				self.current_ascii_line += 1
				self.use_slave()

	def use_slave(self):
		
		slave = self.obtain_slave()

		if slave != None:

			# send the line and set the identifier
			# so we can check when to send the next line

			self.current_ascii_line_id = random_line_color_id(self.id_length)

			if len(self.current_ascii) == self.current_ascii_line:
				self.current_ascii = ""
				self.current_ascii_line = 0
				self.current_ascii_line_id = ""
				return

			slave.send_ascii_line(self.current_ascii_line_id + self.current_ascii[self.current_ascii_line].strip())

	def obtain_slave(self):

		# the current bot number is bigger than the number in the list!!!
		if len(self.loaded_slaves) == 0:
			return None

		self.current_slave += 1

		if self.current_slave >= len(self.loaded_slaves) or (self.use_first_n_bots > 0 and self.current_slave >= self.use_first_n_bots):
			self.current_slave = 0
			return self.loaded_slaves[0]

		return self.loaded_slaves[self.current_slave]

	def create_slave(self, server_host, server_port, channel):

		name = self.slave_nick_prefix + rand_string(7)

		def connect_slave(slave):
			slave.connect(server_host, server_port)
			slave.start_listen(False)

		slave = Slave(name, channel, self.proxy_host, self.proxy_port)
		self.slave_objects[name] = slave

		slave_thread = threading.Thread(target=connect_slave, args=[slave])
		slave_thread.start()

	def remove_loaded_slave(self, nick):
		if nick in self.slave_objects:
			self.loaded_slaves.append(self.slave_objects[nick])

	def add_loaded_slave(self, nick):
		if nick in self.slave_objects:
			self.loaded_slaves.append(self.slave_objects[nick])

	def has_slaves(self):

		return len(self.loaded_slaves) > 0

class Slave(IRCSkeleton):

	def __init__(self, name, default_channel, proxy_host, proxy_port):

		IRCSkeleton.__init__(self, proxy_host, proxy_port)

		self.default_channel = default_channel
		self.nick = name
		self.username = name

	def on_connect(self):

		print("Slave is connected")
		self.join(self.default_channel)

	def send_ascii_line(self, line):

		self.send_message(self.default_channel, line)

herder = Herder("#testing2", "localhost", 7000)
herder.connect("irc.land", 6667)
herder.start_listen(False)