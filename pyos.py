import os
import curses
import pycfg
from pyarch import load_binary_into_memory
from pyarch import cpu_t

PYOS_TASK_STATE_READY                       = 0
PYOS_TASK_STATE_EXECUTING                   = 1

class task_t:
	def __init__ (self):
		self.regs = [0, 0, 0, 0, 0, 0, 0, 0]
		self.reg_pc = 0
		self.stack = 0
		self.paddr_offset = 0
		self.paddr_max = 0
		self.bin_name = ""
		self.bin_size = 0
		self.tid = 0
		self.state = PYOS_TASK_STATE_READY

class os_t:
	def __init__ (self, cpu, memory, terminal):
		self.cpu = cpu
		self.memory = memory
		self.terminal = terminal

		self.terminal.enable_curses()

		self.console_str = ""

		self.the_task = None
		self.next_task_id = 0
		self.tasks = []
		self.current_task = None
		self.next_sched_task = 0
		self.idle_task = None
		#ao inves de manter o idel offset mantem o offet do ultimo
		self.idle_offset = 0
		self.idle_task = self.load_task("idle.bin")
		if self.idle_task is None:
			self.panic("could not load idle.bin task")
		
		self.printk("end load start sched")
		self.sched(self.idle_task)

		self.terminal.console_print("this is the console, type the commands here\n")

	def load_task (self, bin_name):
		if not os.path.isfile(bin_name):
			self.printk("file "+bin_name+" does not exists")
			return None
		if (os.path.getsize(bin_name) % 2) == 1:
			self.printk("file size of "+bin_name+" must be even")
			return None
		
		task = task_t()
		task.bin_name = bin_name
		task.bin_size = os.path.getsize(bin_name) / 2 # 2 bytes = 1 word

		task.paddr_offset, task.paddr_max = self.allocate_contiguos_physical_memory_to_task(task.bin_size, task)

		if task.paddr_offset == -1:
			return None

		task.regs = [0, 0, 0, 0, 0, 0, 0, 0]
		task.reg_pc = 1
		task.stack = 0
		task.state = PYOS_TASK_STATE_READY

		self.printk("allocated physical addresses "+str(task.paddr_offset)+" to "+str(task.paddr_max)+" for task "+task.bin_name+" ("+str(self.get_task_amount_of_memory(task))+" words) (binary has "+str(task.bin_size)+" words)")

		self.read_binary_to_memory(task.paddr_offset, task.paddr_max, bin_name)

		self.printk("task "+bin_name+" successfully loaded")

		task.tid = self.next_task_id
		self.next_task_id = self.next_task_id + 1

		self.tasks.append( task )
		return task

	def read_binary_to_memory (self, paddr_offset, paddr_max, bin_name):
		bpos = 0
		paddr = paddr_offset
		bin_size = os.path.getsize(bin_name) / 2
		i = 0
		with open(bin_name, "rb") as f:
			while True:
				byte = f.read(1)
				if not byte:
					break
				byte = ord(byte)
				if bpos == 0:
					lower_byte = byte
				else:
					word = lower_byte | (byte << 8)
					if paddr > paddr_max:
						self.panic("something really bad happenned when loading "+bin_name+" (paddr > task.paddr_max)")
					self.memory.write(paddr, word)
					paddr = paddr + 1
					i = i + 1
				bpos = bpos ^ 1

		if i != bin_size:
			self.panic("something really bad happenned when loading "+bin_name+" (i != task.bin_size)")

	def sched (self, task):
		if self.current_task is not None:
			self.panic("current_task must be None when scheduling a new one (current_task="+self.current_task.bin_name+")")
		if task.state != PYOS_TASK_STATE_READY:
			self.panic("task "+task.bin_name+" must be in READY state for being scheduled (state = "+str(task.state)+")")

		for i in range(0, 7):
			self.cpu.regs[i] = task.regs[i]
		self.cpu.reg_pc = task.reg_pc
		self.cpu.paddr_offset = task.paddr_offset
		self.cpu.paddr_max = task.paddr_max

		task.state = PYOS_TASK_STATE_EXECUTING

		self.current_task = task
		self.printk("scheduling task "+task.bin_name)
		self.printk("task state "+str(task.state))

	def get_task_amount_of_memory (self, task):
		return task.paddr_max - task.paddr_offset + 1

	# allocate contiguos physical addresses that have $words
	# returns the addresses of the first and last words to be used by the process
	# -1, -1 if cannot find

	def allocate_contiguos_physical_memory_to_task (self, words, task):
		self.printk("memory "+str(self.memory.read(0)))
		self.printk("task size "+str(words))
		maxOffset = 0
		for task in self.tasks:
			if task.paddr_max > maxOffset:
				maxOffset = task.paddr_max
		return maxOffset+1, words+maxOffset+1

	def printk(self, msg):
		self.terminal.kernel_print("kernel: " + msg + "\n")

	def panic (self, msg):
		self.terminal.end()
		self.terminal.dprint("kernel panic: " + msg)
		self.cpu.cpu_alive = False

	def interrupt_keyboard (self):
		key = self.terminal.get_key_buffer()

		if ((key >= ord('a')) and (key <= ord('z'))) or ((key >= ord('A')) and (key <= ord('Z'))) or ((key >= ord('0')) and (key <= ord('9'))) or (key == ord(' ')) or (key == ord('-')) or (key == ord('_')) or (key == ord('.')):
			self.console_str = self.console_str + chr(key)
			self.terminal.console_print("\r" + self.console_str)
		elif key == curses.KEY_BACKSPACE:
			self.console_str = self.console_str[:-1]
			self.terminal.console_print("\r" + self.console_str)
		elif (key == curses.KEY_ENTER) or (key == ord('\n')):
			self.interpret_cmd(self.console_str)
			self.console_str = ""

	def interpret_cmd (self, cmd):
		if cmd == "bye":
			self.cpu.cpu_alive = False
		elif cmd == "tasks":
			self.task_table_print()
		elif cmd == "test":
			self.printk("idle_offset "+str(self.idle_offset))
			self.printk("cpu_offset "+str(self.cpu.paddr_max))
			self.printk("idle_task "+str(self.idle_task.bin_name))
			self.printk("idle_task state "+str(self.idle_task.state))
			self.printk("self.current_task name "+str(self.current_task.bin_name))
			self.printk("self.current_task state "+str(self.current_task.state))
			self.terminal.console_print("\n")
		elif cmd[:3] == "run":
			bin_name = cmd[4:]
			self.terminal.console_print("\rrun binary " + bin_name + "\n")
			task = self.load_task(bin_name)
			if task is None:
				self.terminal.console_print("error: binary " + bin_name + " not found\n")
			# if task is not None:
			# 	if self.the_task is None:
			# 		self.un_sched(self.idle_task)
			# 		self.the_task = task;
			# 		self.sched(self.the_task)
			# 	else:
			# 		self.printk('test thetask')
			# 		self.un_sched(self.the_task)
			# else:
			# 	self.terminal.console_print("error: binary " + bin_name + " not found\n")
		else:
			self.terminal.console_print("\rinvalid cmd " + cmd + "\n")

	def task_table_print(self):
		self.printk('test')
		for task in self.tasks:
			self.printk(
        #"regs: " + task.regs + " " + 
				"reg_pc: " + str(task.reg_pc)+ " " + 
				#"stack: " +task.stack+ " " + 
        "paddr_offset: " + str(task.paddr_offset)+ " " + 
				"paddr_max: " + str(task.paddr_max)+ " " + 
        "bin_name: " + str(task.bin_name)+ " " + 
				"bin_size: " + str(task.bin_size)+ " " + 
        "tid: " + str(task.tid)+ " " + 
				"state: " + str(task.state)
    )
	

	def terminate_unsched_task (self, task):
		if task.state == PYOS_TASK_STATE_EXECUTING:
			self.panic("impossible to terminate a task that is currently running")
		if task == self.idle_task:
			self.panic("impossible to terminate idle task")
		if task is not self.the_task:
			self.panic("task being terminated should be the_task")
		
		self.the_task = None
		self.tasks.remove(task)
		self.printk("task "+task.bin_name+" terminated")

	def un_sched (self, task):
		if task.state != PYOS_TASK_STATE_EXECUTING:
			self.panic("task "+task.bin_name+" must be in EXECUTING state for being scheduled (state = "+str(task.state)+")")
		if task is not self.current_task:
			self.panic("task "+task.bin_name+" must be the current_task for being scheduled (current_task = "+self.current_task.bin_name+")")
		for i in range(0, 7):
			task.regs[i] = self.cpu.get_reg(i)
		task.reg_pc = self.cpu.reg_pc

		task.state = PYOS_TASK_STATE_READY

		self.current_task = None
		self.printk("unscheduling task "+task.bin_name)

	def virtual_to_physical_addr (self, task, vaddr):
		return task.paddr_offset + vaddr

	def check_valid_vaddr (self, task, vaddr):
		paddr = self.virtual_to_physical_addr(self.current_task, vaddr)
		if paddr > task.paddr_max:
			return False
		else:
			return True

	def handle_gpf (self, error):
		task = self.current_task
		self.printk("gpf task "+task.bin_name+": "+error)
		self.un_sched(task)
		self.terminate_unsched_task(task)
		self.sched(self.idle_task)

	def interrupt_timer (self):
		self.printk("timer")
		self.escalate_tasks()

	def escalate_tasks (self):
		# TEST THIS
		if len(self.tasks) == 1:
			return
		if self.current_task == self.idle_task:
			self.un_sched(self.idle_task)
			self.sched(self.tasks[1])
			return
		if len(self.tasks) > 2:
			self.printk("switching tasks")
			# troca a task para a proxima task no array
			# se for a ultima task no array troca pra primeira
			currentTaskIndex = 0
			nextTaskIndex = 0
			for i in range(0, len(self.tasks)):
				if self.tasks[i].tid == self.current_task.tid:
					currentTaskIndex = i
					if i == len(self.tasks)-1:
						self.printk('first task')
						nextTaskIndex = 1
					else:
						self.printk('next task')
						nextTaskIndex = i+1
			self.the_task = self.tasks[nextTaskIndex];
			self.un_sched(self.tasks[currentTaskIndex])
			self.sched(self.tasks[nextTaskIndex])

		

	def handle_interrupt (self, interrupt):
		if interrupt == pycfg.INTERRUPT_MEMORY_PROTECTION_FAULT:
			self.handle_gpf("invalid memory address")
		elif interrupt == pycfg.INTERRUPT_KEYBOARD:
			self.interrupt_keyboard()
		elif interrupt == pycfg.INTERRUPT_TIMER:
			self.interrupt_timer()
		else:
			self.panic("invalid interrupt "+str(interrupt))

	def syscall (self):
		service = self.cpu.get_reg(0)
		task = self.current_task

		if service == 0:
			self.printk("app "+task.bin_name+" request finish")
			self.un_sched(task)
			self.terminate_unsched_task(task)
			self.sched(self.idle_task)
		elif service == 1:
			# self.printk("app "+self.current_task.bin_name+" print string")
			msg0 = self.cpu.memory_load(self.cpu.get_reg(0))
			msg1 = self.cpu.memory_load(self.cpu.get_reg(1))
			self.terminal.app_print("task "+task.bin_name+"\n")
			self.terminal.app_print("print: " + str(msg0) + "\n")
			self.terminal.app_print("print: " + str(msg1) + "\n")
		elif service == 2:
			# self.printk("app "+self.current_task.bin_name+" print new line")
			msg = 'test'
			self.terminal.app_print("\n")
		elif service == 3:
			# self.printk("app "+self.current_task.bin_name+" print int")
			msg = 'test'
			self.terminal.app_print("print: " + msg + "\n")
		else:
			self.handle_gpf("invalid syscall "+str(service))


#pra rodar python2.7 pysim.py
#array de tarefas FEITO
#remover tarefas do array quando terminar FEITO
#gereciador ocupar multiplas tarefas ???
#trocar tarefas com o timer FEITO

