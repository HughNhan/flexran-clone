#/usr/bin/python3

import unittest
from unittest.mock import patch

import pod.cpu

class TestCpuMethods(unittest.TestCase):

    def test_cpus_to_hex_48_cpus(self):
        # Mock out CpuInfo so it doesn't attempt to access system files
        cpuinfo = patch('pod.cpu.CpuInfo')
        cpuinfo.start()
        self.addCleanup(cpuinfo.stop)

        cpulist = pod.cpu.getcpulist('0-47')
        cpuresource = pod.cpu.CpuResource(None, available=cpulist)

        self.assertEqual(cpuresource._cpus_to_hex(cpulist),
                         '0xffffffffffff')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=4),
                         '0xffff 0xffff 0xffff')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=8),
                         '0xffffffff 0xffff')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=12),
                         '0xffffffffffff')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=16),
                         '0xffffffffffff')

    def test_cpus_to_hex_48_cpus_sparse(self):
        # Mock out CpuInfo so it doesn't attempt to access system files
        cpuinfo = patch('pod.cpu.CpuInfo')
        cpuinfo.start()
        self.addCleanup(cpuinfo.stop)

        cpulist = pod.cpu.getcpulist('0,2,4,6,8,10,12,14,16,24,26,28,30,32,34,36,38,40')
        cpuresource = pod.cpu.CpuResource(None, available=cpulist)

        self.assertEqual(cpuresource._cpus_to_hex(cpulist),
                         '0x15555015555')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=4),
                         '0x5555 0x5501 0x155')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=8),
                         '0x55015555 0x155')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=12),
                         '0x15555015555')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=16),
                         '0x15555015555')

    def test_cpus_to_hex_128_cpus(self):
        # Mock out CpuInfo so it doesn't attempt to access system files
        cpuinfo = patch('pod.cpu.CpuInfo')
        cpuinfo.start()
        self.addCleanup(cpuinfo.stop)

        cpulist = pod.cpu.getcpulist('4-63,68-127')
        cpuresource = pod.cpu.CpuResource(None, available=cpulist)

        self.assertEqual(cpuresource._cpus_to_hex(cpulist),
                         '0xfffffffffffffff0fffffffffffffff0')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=16),
                         '0xfffffffffffffff0 0xfffffffffffffff0')

    def test_cpus_to_hex_256_cpus(self):
        # Mock out CpuInfo so it doesn't attempt to access system files
        cpuinfo = patch('pod.cpu.CpuInfo')
        cpuinfo.start()
        self.addCleanup(cpuinfo.stop)

        cpulist = pod.cpu.getcpulist('5-9,42-77,120-220,250-255')
        cpuresource = pod.cpu.CpuResource(None, available=cpulist)

        self.assertEqual(cpuresource._cpus_to_hex(cpulist),
                         '0xfc0000001fffffffffffffffffffffffff00000000003ffffffffc00000003e0')
        self.assertEqual(cpuresource._cpus_to_hex(cpulist, max_segment_len=16),
                         '0xfffffc00000003e0 0xff00000000003fff 0xffffffffffffffff 0xfc0000001fffffff')

    def test_get_free_siblings_mask_64_cpus(self):
        # Mock out CpuInfo so it doesn't attempt to access system files
        cpuinfo = patch('pod.cpu.CpuInfo')
        cpuinfo.start()
        self.addCleanup(cpuinfo.stop)

        status = ("Dummy_entry:\tf\n"
                  "Cpus_allowed_list:\t0-63\n"
                  "Another_dummy_entry:\t1\n")
        cpuresource = pod.cpu.CpuResource(status)

        self.assertEqual(cpuresource.get_free_siblings_mask(1), '0x1')
        self.assertEqual(cpuresource.get_free_siblings_mask(2), '0x3')
        self.assertEqual(cpuresource.get_free_siblings_mask(3), '0x7')
        self.assertEqual(cpuresource.get_free_siblings_mask(4), '0xf')
        self.assertEqual(cpuresource.get_free_siblings_mask(64, max_mask_len=16),
                         '0xffffffffffffffff')
        self.assertRaisesRegex(SystemExit, 'failed to allocate cpu',
                               cpuresource.get_free_siblings_mask, 65)

    def test_get_free_siblings_mask_96_cpus_sparse(self):
        # Mock out CpuInfo so it doesn't attempt to access system files
        cpuinfo = patch('pod.cpu.CpuInfo')
        cpuinfo.start()
        self.addCleanup(cpuinfo.stop)

        status = ("Dummy_entry:\tf\n"
                  "Cpus_allowed_list:\t3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,51,53,55,57,59,61,63,65,67,69,71,73,75,77,79,81\n"
                  "Another_dummy_entry:\t1\n")
        cpuresource = pod.cpu.CpuResource(status)

        self.assertEqual(cpuresource.get_free_siblings_mask(1), '0x8')
        self.assertEqual(cpuresource.get_free_siblings_mask(2), '0x28')
        self.assertEqual(cpuresource.get_free_siblings_mask(3), '0xa8')
        self.assertEqual(cpuresource.get_free_siblings_mask(4), '0x2a8')
        self.assertEqual(cpuresource.get_free_siblings_mask(32), '0x2aaaaaaa80002aaaaaaa8')
        self.assertEqual(cpuresource.get_free_siblings_mask(32, max_mask_len=16),
                         '0xaaa80002aaaaaaa8 0x2aaaa')
        self.assertRaisesRegex(SystemExit, 'failed to allocate cpu',
                               cpuresource.get_free_siblings_mask, 33)

    def test_allocate_siblings_mask_64_cpus(self):
        # Mock out CpuInfo so it doesn't attempt to access system files
        cpuinfo = patch('pod.cpu.CpuInfo')
        cpuinfo.start()
        self.addCleanup(cpuinfo.stop)

        status = ("Dummy_entry:\tf\n"
                  "Cpus_allowed_list:\t0-63\n"
                  "Another_dummy_entry:\t1\n")
        cpuresource = pod.cpu.CpuResource(status)

        self.assertEqual(cpuresource.allocate_siblings_mask(1), '0x1')
        self.assertEqual(cpuresource.allocate_siblings_mask(2), '0x6')
        self.assertEqual(cpuresource.allocate_siblings_mask(3), '0x38')
        self.assertEqual(cpuresource.allocate_siblings_mask(4), '0x3c0')
        self.assertEqual(cpuresource.allocate_siblings_mask(54, 16), '0xfffffffffffffc00')
        self.assertRaisesRegex(SystemExit, 'failed to allocate cpu',
                               cpuresource.get_free_siblings_mask, 1)
