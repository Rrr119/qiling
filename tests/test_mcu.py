#!/usr/bin/env python3
#
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
#

import unittest

import sys
sys.path.append("..")

import os
import struct
import tempfile

from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB

from qiling.core import Qiling
from qiling.const import QL_ARCH, QL_OS, QL_VERBOSE
from qiling.hw.const.stm32f4xx_adc import ADC_SR, ADC_CR2
from qiling.extensions.mcu.stm32f4 import stm32f407, stm32f411, stm32f429
from qiling.extensions.mcu.stm32f1 import stm32f103
from qiling.extensions.mcu.atmel import sam3x8e
from qiling.extensions.mcu.gd32vf1 import gd32vf103


FLASH_BASE = 0x8000000
SRAM_BASE  = 0x20000000

def assemble_thumb(code: str, addr: int) -> bytes:
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    encoding, _ = ks.asm(code, addr=addr)

    return bytes(encoding)

def make_firmware(chunks, isr=None, irqn=0x12):
    """ Assemble Thumb-2 code chunks into a Cortex-M firmware image,
        complete with a vector table holding the reset handler and the
        interrupt handler of `irqn`.
    """

    vec_size = (16 + irqn + 1) * 4

    addr = FLASH_BASE + vec_size
    image = b''
    addrs = []

    for chunk in chunks:
        addrs.append(addr)
        binary = assemble_thumb(chunk, addr)
        image += binary
        addr += len(binary)

    if isr is None:
        isr_entry = 0
    else:
        isr_entry = addr | 1
        image += assemble_thumb(isr, addr)

    vector = struct.pack('<II', SRAM_BASE + 0x20000, addrs[0] | 1)
    vector += b'\x00' * (vec_size - 4 - len(vector))
    vector += struct.pack('<I', isr_entry)

    return vector + image, addrs


class MCUTest(unittest.TestCase):
    def make_firmware_file(self, image: bytes) -> str:
        fd, path = tempfile.mkstemp(suffix='.bin')
        self.addCleanup(os.remove, path)

        with os.fdopen(fd, 'wb') as f:
            f.write(image)

        return path

    def test_mcu_led_stm32f411(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f411/rand_blink.hex"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DISASM)

        # Set verbose=QL_VERBOSE.DEFAULT to find warning
        ql.run(count=1000)

        del ql

    def test_mcu_snapshot_stm32f411(self):
        def create_qiling():
            ql = Qiling(["../examples/rootfs/mcu/stm32f411/hello_usart.hex"],
                        archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411)

            ql.hw.create('usart2')
            ql.hw.create('rcc')

            return ql

        ql1 = create_qiling()
        ql1.run(count=1500)
        buf1 = ql1.hw.usart2.recv()
        print('[1] Received from usart: ', buf1)

        snapshot = ql1.save(hw=True)

        ql2 = create_qiling()
        ql2.restore(snapshot)

        ql2.run(count=500)
        buf2 = ql2.hw.usart2.recv()
        print('[2] Received from usart: ', buf2)

        self.assertEqual(buf1 + buf2, b'Hello USART\n')

        del ql1, ql2

    def test_mcu_usart_input_stm32f411(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f411/md5_server.hex"],
            archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.OFF)

        ql.hw.create('usart2')
        ql.hw.create('rcc')

        ql.run(count=1000)

        ql.hw.usart2.send(b'Hello\n')
        ql.run(count=30000)
        ql.hw.usart2.send(b'USART\n')
        ql.run(count=30000)
        ql.hw.usart2.send(b'Input\n')
        ql.run(count=30000)

        buf = ql.hw.usart2.recv()
        self.assertEqual(buf, b'8b1a9953c4611296a827abf8c47804d7\n2daeb613094400290a24fe5086c68f06\n324118a6721dd6b8a9b9f4e327df2bf5\n')

        del ql

    def test_mcu_patch_stm32f411(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f411/patch_test.hex"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('usart2')
        ql.hw.create('rcc')
        ql.hw.create('gpioa')

        ql.patch(0x80005CA, b'\x00\xBF')
        ql.run(count=4000)

        del ql

    def test_mcu_freertos_stm32f411(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f411/os-demo.elf"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DISABLED)

        ql.hw.create('usart2')
        ql.hw.create('rcc')
        ql.hw.create('gpioa')

        count = 0
        def counter():
            nonlocal count
            count += 1

        ql.hw.gpioa.hook_set(5, counter)

        ql.hw.systick.ratio = 0xff
        ql.run(count=100000)

        self.assertTrue(count >= 5)
        self.assertTrue(ql.hw.usart2.recv().startswith(b'Free RTOS\n' * 5))

        del ql

    def test_mcu_dma_stm32f411(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f411/dma-clock.elf"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('usart2')
        ql.hw.create('dma1')
        ql.hw.create('rcc')

        ql.run(count=200000)
        buf = ql.hw.usart2.recv()

        ## check timestamp
        tick = [int(x) for x in buf.split()]
        for i in range(1, len(tick)):
            assert(4 <= tick[i] - tick[i - 1] <= 6)

        del ql

    def test_mcu_i2c_stm32f411(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f411/i2c-lcd.bin", 0x8000000],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('i2c1')
        ql.hw.create('rcc')
        ql.hw.create('gpioa')
        ql.hw.create('gpiob')

        flag = False
        def indicator():
            nonlocal flag
            flag = True

        ql.hw.gpioa.hook_set(5, indicator)

        class LCD:
            address = 0x3f << 1

            def send(self, data):
                pass

            def step(self):
                pass

        ql.hw.i2c1.connect(LCD())
        ql.run(count=550000)

        self.assertTrue(flag)

        del ql

    def test_mcu_spi_stm32f411(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f411/spi-test.bin", 0x8000000],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('spi1')
        ql.hw.create('rcc')
        ql.hw.create('usart2')
        ql.hw.create('gpioa')

        ql.run(count=30000)
        self.assertTrue(ql.hw.usart2.recv() == b'----------------SPI TEST----------------\najcmfoiblenhakdmgpjclfoibkengajd\nmfpicleohbkdngajcmfoiblenhakdmgp\njclfoibkengajdmfpicleohbkdngajcm\nfoiblenhakdmgpjclfoibkengajdmfpi\ncleohbkdngajcmfoiblenhakdmgpjclf\noibkenhajdmfpicleohbkdngajcmfpib\nlenhakdmgpjclfoibkenhajdmfpicleo\nhbkdngajcmfpiblenhakdmgpjclfoibk\n----------------TEST END----------------\n')

        del ql

    def test_mcu_led_rust_stm32f411(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f411/led-rust.hex"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DEFAULT)

        count = 0
        def counter():
            nonlocal count
            count += 1

        ql.hw.create('gpioa').hook_set(5, counter)
        ql.hw.create('rcc')

        ql.run(count=1000)
        self.assertTrue(count >= 5)

        del ql

    def test_mcu_hacklock_stm32f407(self):
        def crack(passwd):
            ql = Qiling(["../examples/rootfs/mcu/stm32f407/backdoorlock.hex"],
                        archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f407, verbose=QL_VERBOSE.OFF)

            ql.hw.create('spi2')
            ql.hw.create('gpioe')
            ql.hw.create('gpiof')
            ql.hw.create('usart1')
            ql.hw.create('rcc')

            print('Testing passwd', passwd)

            ql.patch(0x8000238, b'\x00\xBF' * 4)
            ql.patch(0x80031e4, b'\x00\xBF' * 11)
            ql.patch(0x80032f8, b'\x00\xBF' * 13)
            ql.patch(0x80013b8, b'\x00\xBF' * 10)

            ql.hw.usart1.send(passwd.encode() + b'\r')

            ql.hw.systick.set_ratio(400)

            ql.run(count=400000, end=0x8003225)

            return ql.arch.effective_pc == 0x8003225

        self.assertTrue(crack('618618'))
        self.assertTrue(crack('778899'))
        self.assertFalse(crack('123456'))

    def test_mcu_tim_speed_stm32f411(self):
        ql = Qiling(['../examples/rootfs/mcu/stm32f411/basic-timer.elf'],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('rcc')
        ql.hw.create('flash interface')
        ql.hw.create('pwr')
        ql.hw.create('gpioa')
        ql.hw.create('usart2')
        ql.hw.create('tim1')


        ql.hw.tim1.set_ratio(1500)
        ql.run(count=2500)

        count = 0
        def counter():
            nonlocal count
            count += 1

        ql.hw.gpioa.hook_set(5, counter)
        ql.run(count=10000)
        count1 = count
        count = 0

        ql.hw.tim1.set_ratio(1400 * 2)
        ql.run(count=10000)
        count2 = count
        count = 0

        ql.hw.tim1.set_ratio(1600 // 2)
        ql.run(count=10000)
        count3 = count
        count = 0

        self.assertTrue(round(count2 / count1) == 2)
        self.assertTrue(round(count1 / count3) == 2)
        self.assertTrue(ql.hw.usart2.recv().startswith(b'hello\n'))

    def test_mcu_i2c_interrupt_stm32f411(self):
        ql = Qiling(['../examples/rootfs/mcu/stm32f411/i2cit-lcd.elf'],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('i2c1')
        ql.hw.create('rcc').watch()
        ql.hw.create('gpioa')
        ql.hw.create('gpiob')

        class LCD:
            address = 0x3f << 1

            def send(self, data):
                pass

            def step(self):
                pass

        lcd = LCD()
        ql.hw.i2c1.connect(lcd)

        ql.hw.systick.set_ratio(100)

        delay_start = 0x8002936
        delay_end = 0x8002955
        def skip_delay(ql):
            ql.arch.regs.pc = delay_end

        ql.hook_address(skip_delay, delay_start)

        ql.run(count=100000)

        del ql

    def test_mcu_blink_gd32vf103(self):
        ql = Qiling(['../examples/rootfs/mcu/gd32vf103/blink.hex'],
                    archtype=QL_ARCH.RISCV, ostype=QL_OS.MCU, env=gd32vf103, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('rcu')
        ql.hw.create('gpioa')
        ql.hw.create('gpioc').watch()

        delay_cycles_begin = 0x800015c
        delay_cycles_end = 0x800018c

        def skip_delay(ql):
            ql.arch.regs.pc = delay_cycles_end

        count = 0
        def counter():
            nonlocal count
            count += 1

        ql.hook_address(skip_delay, delay_cycles_begin)
        ql.hw.gpioc.hook_set(13, counter)
        ql.run(count=20000)
        self.assertTrue(count > 350)

        del ql

    def test_mcu_crc_stm32f407(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f407/ai-sine-test.elf"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f407, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('rcc')
        ql.hw.create('pwr')
        ql.hw.create('flash interface')
        ql.hw.create('gpioa')
        ql.hw.create('gpiob')
        ql.hw.create('gpiod')
        ql.hw.create('spi1')
        ql.hw.create('crc')
        ql.hw.create('dbgmcu')

        flag = False
        def indicator(ql):
            nonlocal flag
            ql.log.info('PA7 set')
            flag = True

        ql.hw.gpioa.hook_set(7, indicator, ql)
        ql.hw.systick.ratio = 1000

        ql.run(count=600000)
        self.assertTrue(flag)

        del ql

    def test_mcu_usart_stm32f103(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f103/sctf2020-password-lock-plus.hex"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f103, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('rcc')
        ql.hw.create('flash interface')
        ql.hw.create('exti')
        ql.hw.create('usart1')
        ql.hw.create('gpioa')
        ql.hw.create('afio')
        ql.hw.create('dma1').watch()

        data = []
        def gpio_set_cb(pin):
            data.append(pin)

        ql.hw.gpioa.hook_set(1, gpio_set_cb, '1')
        ql.hw.gpioa.hook_set(2, gpio_set_cb, '2')
        ql.hw.gpioa.hook_set(3, gpio_set_cb, '3')
        ql.hw.gpioa.hook_set(4, gpio_set_cb, '4')

        ql.run(count=400000)

        self.assertTrue((''.join(data)).find('1442413') != -1)
        self.assertTrue(ql.hw.usart1.recv()[:23] == b'SCTF{that1s___r1ghtflag')

        del ql

    def test_mcu_serial_sam3x8e(self):
        ql = Qiling(["../examples/rootfs/mcu/sam3x8e/serial.ino.hex"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=sam3x8e, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('wdt')
        ql.hw.create('efc0')
        ql.hw.create('efc1')
        ql.hw.create('pmc')
        ql.hw.create('uotghs')
        ql.hw.create('pioa')
        ql.hw.create('piob')
        ql.hw.create('pioc')
        ql.hw.create('piod')
        ql.hw.create('adc')
        ql.hw.create('uart')
        ql.hw.create('pdc_uart')

        ql.hw.systick.ratio = 1000
        ql.run(count=100000)
        self.assertTrue(ql.hw.uart.recv().startswith(b'hello world\nhello world\n'))

        del ql

    def test_mcu_hackme_stm32f429(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f429/bof.elf"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f429, verbose=QL_VERBOSE.DISABLED)

        ql.hw.create('rcc')
        ql.hw.create('usart2')
        ql.hw.create('usart3')

        snapshot = ql.save(hw=True)

        ql.restore(snapshot)
        ql.hw.usart3.send(b'hbckme\nabc\n')
        ql.run(count=20000)

        self.assertEqual(ql.hw.usart2.recv(), b'')
        self.assertEqual(ql.hw.usart3.recv(), b'Wrong password!\n')

        ql.restore(snapshot)
        ql.hw.usart3.send(b'hackme\naaaaaaaaaaaaaaaaaaaa\xa9\x05\n')
        ql.run(count=40000)

        self.assertEqual(ql.hw.usart2.recv(), b'Nice Hack!\n')
        self.assertEqual(ql.hw.usart3.recv(), b'Welcome to the world of Hacking!\naaaaaaaaaaaaaaaaaaaa\xa9\x05\n')

    def test_mcu_fastmode_stm32f429(self):
        ql = Qiling(["../examples/rootfs/mcu/stm32f429/bof.elf"],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f429, verbose=QL_VERBOSE.DEFAULT)

        ql.hw.create('rcc')
        ql.hw.create('usart2')
        ql.hw.create('usart3')

        ql.hw.usart3.send(b'hackme\naaaaaaaaaaaaaaaaaaaa\xa9\x05\n')

        ql.os.fast_mode = True
        ql.run(timeout=400)

        self.assertEqual(ql.hw.usart2.recv(), b'Nice Hack!\n')
        self.assertEqual(ql.hw.usart3.recv(), b'Welcome to the world of Hacking!\naaaaaaaaaaaaaaaaaaaa\xa9\x05\n')

    def test_mcu_adc_poll_stm32f411(self):
        # firmware: start a regular conversion, poll SR.EOC, read DR and
        # store the result and the post-read SR into SRAM
        main = '''
            movw r0, #0x2000
            movt r0, #0x4001
            mov  r1, #1
            str  r1, [r0, #8]
            movw r1, #0x0001
            movt r1, #0x4000
            str  r1, [r0, #8]
        poll:
            ldr  r2, [r0]
            tst  r2, #2
            beq  poll
            ldr  r3, [r0, #0x4c]
            movw r4, #0x0000
            movt r4, #0x2000
            str  r3, [r4]
            ldr  r2, [r0]
            str  r2, [r4, #4]
        done:
            b    done
        '''

        image, _ = make_firmware([main])
        path = self.make_firmware_file(image)

        ql = Qiling([path, FLASH_BASE],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.OFF)

        ql.hw.create('adc1')
        ql.hw.adc1.data = 0xabc

        ql.run(count=100)

        # converted value reached the firmware
        self.assertEqual(ql.mem.read_ptr(SRAM_BASE), 0xabc)
        # EOC was cleared by reading DR
        self.assertEqual(ql.mem.read_ptr(SRAM_BASE + 4) & ADC_SR.EOC, 0)
        # SWSTART is self-clearing
        self.assertEqual(ql.hw.adc1.instance.CR2 & ADC_CR2.SWSTART, 0)

        del ql

    def test_mcu_adc_interrupt_stm32f411(self):
        # firmware: enable the ADC interrupt in the NVIC, start a conversion
        # with EOCIE set and wait for the ISR to deliver the result
        main = '''
            movw r0, #0xe100
            movt r0, #0xe000
            movw r1, #0x0000
            movt r1, #0x0004
            str  r1, [r0]
            movw r0, #0x2000
            movt r0, #0x4001
            mov  r1, #32
            str  r1, [r0, #4]
            movw r1, #0x0001
            movt r1, #0x4000
            str  r1, [r0, #8]
            movw r4, #0x0000
            movt r4, #0x2000
        wait:
            ldr  r5, [r4, #4]
            cmp  r5, #0
            beq  wait
        done:
            b    done
        '''

        isr = '''
            movw r0, #0x2000
            movt r0, #0x4001
            ldr  r1, [r0, #0x4c]
            movw r2, #0x0000
            movt r2, #0x2000
            str  r1, [r2]
            mov  r3, #1
            str  r3, [r2, #4]
            bx   lr
        '''

        image, _ = make_firmware([main], isr=isr)
        path = self.make_firmware_file(image)

        ql = Qiling([path, FLASH_BASE],
                    archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.OFF)

        ql.hw.create('adc1')
        ql.hw.adc1.data = 0xdef

        ql.run(count=200)

        # the ISR ran and handed the converted value to the firmware
        self.assertEqual(ql.mem.read_ptr(SRAM_BASE), 0xdef)
        self.assertEqual(ql.mem.read_ptr(SRAM_BASE + 4), 1)

        del ql

    def test_mcu_adc_snapshot_stm32f411(self):
        # firmware part1 starts a conversion, part2 polls and stores the
        # result; snapshot the peripheral between the two stages
        part1 = '''
            movw r0, #0x2000
            movt r0, #0x4001
            movw r1, #0x0001
            movt r1, #0x4000
            str  r1, [r0, #8]
        '''

        part2 = '''
        poll:
            ldr  r2, [r0]
            tst  r2, #2
            beq  poll
            ldr  r3, [r0, #0x4c]
            movw r4, #0x0000
            movt r4, #0x2000
            str  r3, [r4]
        done:
            b    done
        '''

        image, addrs = make_firmware([part1, part2])
        path = self.make_firmware_file(image)

        def create_qiling():
            ql = Qiling([path, FLASH_BASE],
                        archtype=QL_ARCH.CORTEX_M, ostype=QL_OS.MCU, env=stm32f411, verbose=QL_VERBOSE.OFF)

            ql.hw.create('adc1')
            ql.hw.adc1.data = 0x5aa

            return ql

        ql1 = create_qiling()
        ql1.run(end=addrs[1] | 1)  # Cortex-M end addresses carry the Thumb bit

        # conversion completed, EOC is part of the snapshot
        self.assertTrue(ql1.hw.adc1.instance.SR & ADC_SR.EOC)

        snapshot = ql1.save(hw=True)

        ql2 = create_qiling()
        ql2.restore(snapshot)

        self.assertTrue(ql2.hw.adc1.instance.SR & ADC_SR.EOC)

        reads = []
        ql2.hw.adc1.hook_read(lambda periph, access, offset, size, value: reads.append(offset))
        ql2.run(count=100)

        self.assertEqual(ql2.mem.read_ptr(SRAM_BASE), 0x5aa)
        self.assertIn(ql2.hw.adc1.struct.DR.offset, reads)

        del ql1, ql2


if __name__ == "__main__":
    unittest.main()

