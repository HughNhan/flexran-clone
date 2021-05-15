package main

import (
	"io/ioutil"
	"reflect"
	"strings"
	"testing"
)

const (
	cpusAllowedList = "Cpus_allowed_list"
	statusFile      = "/tmp/self_status"
)

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func TestGetAllowedCpus(t *testing.T) {
	cases := []struct {
		content string
		spaces  int
	}{
		{"0-15", 5},
		{"0,1", 5},
	}

	for _, line := range cases {
		status := cpusAllowedList + ":" + strings.Repeat(" ", line.spaces) + line.content + "\n"
		err := ioutil.WriteFile(statusFile, []byte(status), 0644)
		check(err)
		got, err := getAllowedCpus(statusFile)
		check(err)
		if got != line.content {
			t.Errorf("getAllowedCpus(%q) == %q, want %q", statusFile, got, line.content)
		}
	}

}

func TestString(t *testing.T) {
	cases := []struct {
		bitmap Bitmap
		want   string
	}{
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0}, "0x8000000"},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}, "0x1"},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}, "0x0"},
	}
	for _, testCase := range cases {
		bitmapStr := testCase.bitmap.String()
		if bitmapStr != testCase.want {
			t.Errorf("bitmap.String() output %q, want %q", bitmapStr, testCase.want)
		}
	}
}

func TestSetBitMap(t *testing.T) {
	cases := []struct {
		origin Bitmap
		cpu    int
		want   Bitmap
	}{
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0}, 0, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 1}},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0}, 1, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 2}},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0}, 8, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 1, 0}},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0}, 127, [16]byte{128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0}},
	}

	for _, testCase := range cases {
		testCase.origin.Set(testCase.cpu)
		if testCase.origin != testCase.want {
			t.Errorf("bitmap.Set() actual output %q, want %q", testCase.origin, testCase.want)
		}
	}
}

func TestClearBitMap(t *testing.T) {
	cases := []struct {
		origin Bitmap
		cpu    int
		want   Bitmap
	}{
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}, 0, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2}, 1, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1}, 8, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}},
		{[16]byte{128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0}, 127, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0}},
	}
	for _, testCase := range cases {
		testCase.origin.Clear(testCase.cpu)
		if testCase.origin != testCase.want {
			t.Errorf("bitmap.Clear() actual output %q, want %q", testCase.origin, testCase.want)
		}
	}
}

func TestSets(t *testing.T) {
	cases := []struct {
		origin Bitmap
		cpu    []int
		want   Bitmap
	}{
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}, []int{0, 1}, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3}},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2}, []int{0, 1}, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3}},
	}
	for _, testCase := range cases {
		testCase.origin.Sets(testCase.cpu...)
		if testCase.origin != testCase.want {
			t.Errorf("bitmap.Sets() actual output %q, want %q", testCase.origin, testCase.want)
		}
	}
}

/* TODO. This test case is machine specific, expected to work on machine with 8 HT, 0/4 sibling.
func TestNewCpuBitMap(t *testing.T) {
	cases := []struct {
		cpuStr       string
		allowSibling bool
		want         Bitmap
	}{
		{"0,4", true, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 17}},
		{"0,4", false, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}},
		{"0-5", true, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 63}},
		{"0-5", false, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15}},
	}
	for _, testCase := range cases {
		status := cpusAllowedList + ":" + strings.Repeat(" ", 1) + testCase.cpuStr + "\n"
		err := ioutil.WriteFile(statusFile, []byte(status), 0644)
		check(err)
		pBitmap := NewCpuBitMap(testCase.allowSibling, statusFile)
		if *pBitmap != testCase.want {
			t.Errorf("NewCpuBitMap() actual output %q, want %q", *pBitmap, testCase.want)
		}
	}
}
*/

func TestAllocateCpu(t *testing.T) {
	cases := []struct {
		bitsOrigin Bitmap
		cpus       int
		want       []int
		bitsAfter  Bitmap
	}{
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}, 1, []int{0}, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3}, 1, []int{0}, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2}},
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7}, 2, []int{0, 1}, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4}},
	}
	for _, testCase := range cases {
		got := testCase.bitsOrigin.AllocateCpu(testCase.cpus)
		if !reflect.DeepEqual(testCase.want, got) {
			t.Errorf("AllocateCpu() produce array %q, want %q", got, testCase.want)
		}
		// after cpu allocate, origin will change
		if testCase.bitsOrigin != testCase.bitsAfter {
			t.Errorf("after AllocateCpu(), expected bitmap %q, got %q", testCase.bitsAfter, testCase.bitsOrigin)
		}
	}
}

func TestAllocateCpuHexStr(t *testing.T) {
	cases := []struct {
		bitsOrigin Bitmap
		num        int
		want       string
	}{
		{[16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}, 1, "0x1"},
		{[16]byte{128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2}, 1, "0x2"},
		{[16]byte{128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3}, 2, "0x3"},
	}
	for _, testCase := range cases {
		got := testCase.bitsOrigin.AllocateCpuHexStr(testCase.num)
		if got != testCase.want {
			t.Errorf("AllocateCpuHexStr() produce %q, want %q", got, testCase.want)
		}
	}
}

func TestCopyBitMap(t *testing.T) {
	cases := []struct {
		bitsOrigin Bitmap
		low        int
		high       int
		want       Bitmap
	}{
		{[16]byte{128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}, 0, 63, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}},
		{[16]byte{128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1}, 64, 127, [16]byte{128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}},
		{[16]byte{128, 0, 0, 0, 0, 0, 0, 0, 127, 0, 0, 0, 0, 0, 0, 1}, 0, 63, [16]byte{0, 0, 0, 0, 0, 0, 0, 0, 127, 0, 0, 0, 0, 0, 0, 1}},
	}

	for _, testCase := range cases {
		got := testCase.bitsOrigin.CopyBitMap(testCase.low, testCase.high)
		if *got != testCase.want {
			t.Errorf("CopyBitMap(), expected bitmap %q, got %q", testCase.want, *got)
		}
	}
}
