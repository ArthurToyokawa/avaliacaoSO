import os
import curses
import pycfg
from pyarch import load_binary_into_memory
from pyarch import cpu_t

class os_t:
	def __init__ (self, cpu, memory, terminal):
		self.cpu = cpu
		self.memory = memory
		self.terminal = terminal

		self.terminal.enable_curses()

		self.console_str = ""
		self.terminal.console_print("this is the console, type the commands here\n")
	#chama pra printar no console
	def printk(self, msg):
		self.terminal.kernel_print("kernel: " + str(msg) + "\n")
	#se deu merda chama
	def panic (self, msg):
		self.terminal.end()
		self.terminal.dprint("kernel panic: " + msg)
		self.cpu.cpu_alive = False

	def run_command(self, command):
		self.printk('command' + str(command))
		if command == 'stop':
			self.cpu.cpu_alive = False
		else:
			self.terminal.console_print("comando nao reconhecido\n")
		self.console_str = ""

	def interrupt_keyboard (self):
		key = self.terminal.get_key_buffer()
		if ((key >= ord('a')) and (key <= ord('z'))) or ((key >= ord('A')) and (key <= ord('Z'))) or ((key >= ord('0')) and (key <= ord('9'))) or (key == ord(' ')) or (key == ord('-')) or (key == ord('_')) or (key == ord('.')):
			strchar = chr(key)
			self.console_str += strchar
			self.terminal.console_print(strchar)
		elif key == curses.KEY_BACKSPACE:
			if len(self.console_str) > 0:
				self.console_str = self.console_str.rstrip(self.console_str[-1])
				self.terminal.console_print('\r')
				self.terminal.console_print(" " + self.console_str)
			return
		elif (key == curses.KEY_ENTER) or (key == ord('\n')):
			strchar = chr(key)
			self.terminal.console_print(strchar)
			self.run_command(self.console_str)
			return
	#chama toda vez que receber interrupcao
	def handle_interrupt (self, interrupt):
		if interrupt == pycfg.INTERRUPT_KEYBOARD:
			self.interrupt_keyboard()
		return
	#chamada de sistema implementar
	def syscall (self):
		#self.terminal.app_print(msg)
		return
	

#quando digitar qualquer tecla aparece no terminal, quando der backspace retira caractere quando enter mandar o comando
#implementar um comando de fechar o terminal e outro que chama uma funcao teste para carregar commando
#printar para console e nao no kprint

#pra rodar python2.7 pysim.py
#todo codigo vai aqui
#console print para print de processos