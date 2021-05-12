package main

import (
	"encoding/hex"
	"fmt"
	"strconv"
	"strings"
)

// each byte represents 8 cpus,e.g. 16 means 16*8=128 CPUs
const bitmapBytes = 16

type Bitmap [bitmapBytes]byte

func (bits *Bitmap) IsSet(i int) bool {
	return bits[bitmapBytes-1-i/8]&(1<<uint(i%8)) != 0
}

func (bits *Bitmap) Set(i int) {
	bits[bitmapBytes-1-i/8] |= 1 << uint(i%8)
}

func (bits *Bitmap) Clear(i int) {
	bits[bitmapBytes-1-i/8] &^= 1 << uint(i%8)
}

func (bits *Bitmap) Sets(xs ...int) {
	for _, x := range xs {
		bits.Set(x)
	}
}

// find and clear next bit position that is set
func (bits *Bitmap) FindAndClear() (int, error) {
	i := 0
	for i < bitmapBytes*8 {
		if bits.IsSet(i) {
			// clear this bit so next time won't land on this bit
			bits.Clear(i)
			return i, nil
		}
		i += 1
	}
	return -1, fmt.Errorf("Failed to find next bit set")
}

func (bits Bitmap) String() string {
	strNoLeadingZero := strings.TrimLeft(hex.EncodeToString(bits[:]), "0")
	// for all 0 string, make it 0x0
	if strNoLeadingZero == "" {
		strNoLeadingZero = "0"
	}
	return "0x" + strNoLeadingZero
}

func (bits *Bitmap) CopyBitMap(low int, high int) *Bitmap {
	var newBits Bitmap
	for i := low; i <= high; i++ {
		if bits.IsSet(i) {
			newBits.Set(i)
		}
	}
	return &newBits
}

// parse string like 0-1,3,5-8
func ParseCPUStr(s string) (*Bitmap, error) {
	var bits Bitmap
	// Handle empty string.
	if s == "" {
		return &bits, nil
	}

	// Split CPU list string:
	// "0-5,34,46-48 => ["0-5", "34", "46-48"]
	ranges := strings.Split(s, ",")

	for _, r := range ranges {
		boundaries := strings.Split(r, "-")
		if len(boundaries) == 1 {
			// Handle ranges that consist of only one element like "34".
			elem, err := strconv.Atoi(boundaries[0])
			if err != nil {
				return &bits, err
			}
			bits.Set(elem)
		} else if len(boundaries) == 2 {
			// Handle multi-element ranges like "0-5".
			start, err := strconv.Atoi(boundaries[0])
			if err != nil {
				return &bits, err
			}
			end, err := strconv.Atoi(boundaries[1])
			if err != nil {
				return &bits, err
			}
			// Add all elements to the result.
			// e.g. "0-5", "46-48" => [0, 1, 2, 3, 4, 5, 46, 47, 48].
			for e := start; e <= end; e++ {
				bits.Set(e)
			}
		}
	}
	return &bits, nil
}
