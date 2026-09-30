<!--
SPDX-FileCopyrightText: 2026 GARDENA GmbH

SPDX-License-Identifier: GPL-3.0-or-later
-->

Receiving FEC-coded SUN FSK
===========================

Protocol notes for adding forward error correction to the receiver.
Everything here was established while making a separate, hardware-based
Wi-SUN sniffer decode coded traffic, and most of it was measured against
real frames rather than read out of the standard — in one central case
because reading the standard the obvious way produces a decoder that
recovers nothing at all.

References are to IEEE 802.15.4-2020 unless stated otherwise. Nothing
below is specific to a transceiver or to that sniffer's firmware.

This is now implemented here: the bit manipulation is in `lib/fec.cc`,
the header decode in `correlate_sync_word_bb`, and the frame decode in
`pdu_fec_decode`, with a reference encoder in `python/wisun/fec.py`. One
claim below has been corrected against traffic from a second transmitter
in the course of that — see "The padding value is not something to rely
on".


Which operating modes are coded
-------------------------------

A Wi-SUN PhyModeID packs two fields: `PhyModeID = PhyType << 4 | PhyMode`
(Wi-SUN PHY 2.03). PhyType 0 is plain FSK, PhyType 1 is FSK with the
NRNSC forward error correction described here — which `parameters.py`
already names. So every coded mode is its uncoded counterpart plus
`0x10`:

| uncoded | coded | symbol rate | modulation index |
|---------|-------|-------------|------------------|
| 0x01    | 0x11  | 50 ksym/s   | 0.5              |
| 0x03    | 0x13  | 100 ksym/s  | 0.5              |
| 0x05    | 0x15  | 150 ksym/s  | 0.5              |

**A coded mode changes nothing below the bits.** Symbol rate, deviation,
modulation index and channel spacing are identical to the uncoded mode of
the same PhyMode, so the whole receive chain up to and including the bit
slicer is unchanged. FEC is entirely a question of what the recovered bit
stream means.

FEC is optional and additive in the FAN profile: a network may use it,
and if it does, every frame on that PHY is coded. ChanPlanID 33 (EU)
pairs with PhyModeID 0x03/0x13/0x05/0x15, which is the pairing the coded
traffic measured here used (ChanPlanID 33, PhyModeID 0x13, channel 0).


How a coded frame announces itself
----------------------------------

**There is no FEC bit in the PHY header.** Coding is signalled purely by
which start-of-frame delimiter the transmitter sends. For 2-FSK with
`phySunFskSfd = 0`:

| frame    | SFD      |
|----------|----------|
| uncoded  | `0x904E` |
| coded    | `0x6F4E` |

These are bit sequences on the air, in the order the SFD table prints
them, so a correlator that already matches `0x904E` needs only the second
constant to acquire coded frames. The SHR — preamble and SFD — is itself
never coded, interleaved or whitened.

Two consequences worth designing around:

- A receiver locked to one SFD is deaf to the other. Coded and uncoded
  networks can share a channel, and a sniffer that wants both has to
  correlate against both patterns concurrently and carry "which SFD
  matched" forward, because nothing later in the frame will tell it.
- The PHR that follows is *inside* the coded block, so it cannot be read
  until some decoding has happened. See below — this turns out to be
  cheap, not expensive.


The order the transmitter does things — the central fact
--------------------------------------------------------

This is the part that is easy to get wrong, and getting it wrong yields a
decoder that produces nothing recognisable while looking correct.

A transmitter builds a coded frame like this:

1. Concatenate PHR and PSDU, append 3 zero tail bits, then pad to a whole
   number of interleaver blocks.
2. Convolutionally encode the whole of that (19.3.5).
3. Interleave the resulting code symbols, in 16-symbol blocks (19.3.6).
4. Whiten — **only the PSDU's code symbols**. The encoded PHY header,
   which is exactly the first interleaver block, is left alone (19.4,
   deferring to 16.2.3).
5. Prepend the uncoded SHR.

So the shape of a frame on air is:

| part                                          | encoded | interleaved | whitened |
|-----------------------------------------------|---------|-------------|----------|
| SHR (preamble, coded SFD `0x6F4E`)            | no      | no          | no       |
| PHY header — exactly the first block, 4 octets| yes     | yes         | **no**   |
| PSDU                                          | yes     | yes         | **yes**  |

Receiving is that backwards:

1. De-whiten everything past the first 4 coded octets, with the PN9
   generator starting from its seed at the first PSDU code symbol.
2. Deinterleave.
3. Viterbi decode.

What falls out is the PHY header followed by the PSDU **already in
plaintext**. There is no second de-whitening step, and applying one
destroys the frame.

### Why the standard appears to say otherwise

Read casually, clause 19 looks like it whitens the PSDU first and encodes
afterwards. It does not, and the confusion is an artefact of reading the
clauses out of order. 19.3.2 is the *reference modulator* — a
transmit-side data flow — and the steps follow its numbering: 19.3.5 the
coding, 19.3.6 the interleaving, and only then 19.4 the whitening. 19.4
defers to 16.2.3, which starts the generator at "the first bit of the
PSDU"; in a coded frame that is the PSDU's first *code symbol*, and the
encoded header ahead of it is untouched. Both halves of the measurement
are in the text.

The trap is carrying over "whitening covers the PSDU, never the header"
from the uncoded PHY, where it means the PSDU's own octets. A decoder
built on that reading hands whitened symbols to a Viterbi decoder, which
cannot distinguish them from noise, so every experiment comes back empty
for the right reason and the wrong cause.


The convolutional code
----------------------

Rate 1/2, constraint length 4, non-recursive non-systematic (19.3.5).
Three memory elements, so an 8-state trellis — small enough to hand-roll;
no library is warranted.

With `b(i)` the current input bit and `b(i-1)`, `b(i-2)`, `b(i-3)` the
three previous ones:

```
u1(i) = NOT ( b(i) XOR b(i-2) XOR b(i-3) )          G1 = 1 + x^2 + x^3
u0(i) = NOT ( b(i) XOR b(i-1) XOR b(i-2) XOR b(i-3) )   G0 = 1 + x + x^2 + x^3
```

`u1` is transmitted first.

**Both outputs are complemented.** That `NOT` is easy to miss when
reading the figure, and omitting it gives a decoder that inverts every
bit it recovers — which looks like a bit-order or polarity bug and is
neither.

Termination is a zero tail: 3 zero bits, which return the encoder to the
zero state because the code is non-recursive. Note that the padding
described below follows the tail rather than preceding it, so the tail
alone does not leave the encoder terminated.

### The padding value is not something to rely on

**A decoder must trace back from the best surviving state, not from state
0.** The padding bits that follow the tail are not necessarily zeros, so
the encoder is not necessarily back in the zero state when the frame
ends.

The traffic this document was first written from padded with zeros: real
frames decoded with *no* corrections against a reference encoder that
padded with zeros, which they would not have if that transmitter had
padded with anything else.

Frames from a second transmitter, recorded later with this module and
kept as the coded samples in the `gr-wisun-test-suite` repository, pad
with **ones**. The evidence is the same in form and just as strong:
re-encoding each decoded frame against the received code symbols gives
zero mismatches with all-ones padding, and 6 or 14 mismatches — one per
padding bit, plus the tail of the trellis — with zero padding. Those
frames end in state 7, and tracing back from state 0 costs a path metric
of 4 on an otherwise perfect frame.

So the padding value is a property of the transmitter rather than of the
PHY, and nothing may be concluded from the tail and padding bits of a
received frame. Tracing back from the best surviving state costs nothing,
is more forgiving on a damaged frame, and lets the same traceback serve
the early, unterminated header decode described further down. Tracing
back from state 0 instead does not merely lose the last three bits, which
are discarded anyway — it inflates the path metric, and the metric is the
one oracle worth trusting (see below).


Padding and length arithmetic
-----------------------------

After PHR + PSDU + 3 tail bits, the block is padded to a whole number of
16-bit interleaver blocks. The standard gives the padding as 5 or 13
bits, which is the same as saying tail and padding together occupy one
whole octet when `PHR + PSDU` is an odd number of octets, and two when it
is even.

That makes the on-air length a closed form:

```
octets    = psdu_len + 2                      # PSDU plus the 2-octet PHR
info_bits = (octets + (1 if octets odd else 2)) * 8
coded_len = info_bits * 2 / 8                 # octets on air, rate 1/2
```

**The Frame Length field in a coded PHR counts the frame before it was
encoded** — roughly half what arrives. Any framing driven by that field
directly will stop halfway through every frame.

Worked values, including the frame sizes seen on the network measured:

| PSDU | coded octets | ratio |
|------|--------------|-------|
| 50   | 108          | 2.16  |
| 56   | 120          | 2.14  |
| 142  | 292          | 2.06  |
| 169  | 344          | 2.04  |
| 198  | 404          | 2.04  |
| 2047 | 4100         | 2.00  |

The symbol rate on air is unchanged, so a coded PHY costs very close to
half the payload throughput of its uncoded counterpart — the ratio
approaches 2.00 as frames grow, with the overhead above that being the
PHR, tail and padding.


The interleaver
---------------

A block interleaver over 16 code symbols — 32 coded bits — permuting
whole symbols rather than individual bits (19.3.6):

```
q(p)(k) = a(p)(t),   t = 15 - 4*(k mod 4) - floor(k/4)
```

Undoing it is a direct reading: the symbol received k-th belongs at
position `t`. There is no state between blocks, so deinterleaving is a
fixed 16-entry shuffle applied repeatedly.

### The block size is the same 16 bits as the PHY header

This is not a coincidence to admire but the thing that makes a coded
frame receivable without buffering the largest frame the PHY allows:

- the first interleaver block holds exactly the encoded PHY header,
- it is the one part of the frame that is **not** whitened, so it needs
  no PN9 state to read,
- so it can be deinterleaved and decoded on its own, straight off the
  first 4 octets, giving the Frame Length,
- and `coded_len` above turns that into the true on-air length.

Decoding those 16 bits is not a terminated decode — the code runs on past
the block — so trace back from the best surviving path instead of from
state 0. With three memory elements the survivors have long since merged,
so the result is the same 16 bits the eventual full decode produces.


Whitening (PN9)
---------------

Generator `x^9 + x^5 + 1`, seeded all ones (`0x1FF`), per 16.2.3.

**The bit that comes out is the feedback term itself, `b0 XOR b5`, not a
bit of the register.** That is what makes the sequence open

```
0000 1111 0111 ...
```

rather than with the seed. Getting it wrong still yields a plausible
pseudo-random sequence — just not this one — so check any implementation
against the 30 bits the standard prints before trusting it.

The mask is applied least-significant-bit-first within each octet, which
matches the transmission order of everything except the PHR.

For a coded frame the generator starts at the first PSDU code symbol,
i.e. after 4 coded octets. An existing uncoded whitening block therefore
needs two changes to serve here: it must run on the *code symbols* rather
than on decoded data, and it must skip the first 4 octets before starting
the generator.


Bit order
---------

**The PHY header is transmitted most-significant-bit first; everything
else in the frame is least-significant-bit first.** This holds for both
coded and uncoded frames and is load-bearing: read the decoded header's
bits the way the PSDU's are read and a real header `0x088E` comes out as
`0x1071`.

It is worth returning a decoded PHR as a 16-bit value rather than as two
octets, since there is no octet order that is not a trap for someone.


PHY header fields
-----------------

Figure 19-4. Read as a 16-bit value assembled MSB-first:

| mask     | meaning                                             |
|----------|-----------------------------------------------------|
| `0x07FF` | Frame Length in octets — pre-FEC, see above         |
| `0x0800` | PSDU is whitened                                    |
| `0x1000` | FCS type: 0 = 4-octet, 1 = 2-octet                  |
| `0xE000` | reserved, zero in every frame measured              |

Reference values decoded off the air:

- `0x088E` — 142-octet PSDU, whitened, 4-octet FCS
- `0x0846` — 70-octet PSDU, whitened, 4-octet FCS

FCS-32 is the ordinary Ethernet CRC-32 — reflected, seeded and inverted
with all ones — transmitted least-significant octet first. FCS-16 is
ITU-T CRC-16 seeded with zeroes.


Receiving, end to end
---------------------

1. Correlate for the coded SFD `0x6F4E` (and `0x904E` too if both kinds
   of network are of interest).
2. Collect 4 coded octets. Deinterleave and Viterbi decode them, tracing
   back from the best path, to get the PHR. Do **not** de-whiten these.
3. Take the Frame Length from the PHR, compute `coded_len`, and collect
   that many octets in total.
4. De-whiten octets 4 onwards, PN9 from its seed.
5. Deinterleave every block; Viterbi decode the lot, tracing back from
   the best surviving state — the frame does not necessarily end in the
   zero state, because the padding bits are not necessarily zeros.
6. Drop the first two decoded octets — the header, already read — and
   the tail and padding at the end. What remains is the PSDU. Do not
   check the tail and padding bits against anything.
7. Check the FCS as usual.


Verifying an implementation
---------------------------

### Use the Viterbi path metric as the oracle, not the FCS

The survivor's accumulated metric is the number of received bits the
decoder had to overrule. Against true code symbols it is near zero;
against anything else it settles around **0.25 per code symbol**, because
a random bit pair disagrees with the best available branch about a
quarter of the time.

That makes it a far better search oracle than the FCS when nothing works
yet, because it needs neither correct frame alignment nor a correct guess
at the whitening — it will report structure in a stream that is still
mis-framed. The FCS answers only yes or no, and answers no for every
reason at once.

This is what eventually located the whitening span described above: a
search over PN9 phase scored by path metric dropped every capture from
0.25 to near zero at a single value, where thousands of FCS trials had
returned nothing usable. **Use the metric while it is all still wrong;
switch to the FCS once it is nearly right.**

### A clean link decodes with exactly zero corrections

On a bench, with transmitter and receiver close together, a real frame
needs *no* corrections at all — the uncoded path shows the same. A metric
of "nearly zero" is not success; it means something in the chain is
slightly wrong and is worth chasing to zero.

That is how the whitening span gave itself away a second time: a decoder
that whitened the header along with the PSDU sat at exactly five symbol
errors per frame, every one of them inside the first interleaver block.

The count also makes a useful runtime guard. Anything above about an
eighth of the symbols is not a damaged frame, it is not a frame — a
16-bit FCS accepts noise once in 65536, and a plausible-looking Frame
Length alone cannot tell you otherwise.

### Things worth testing offline

All of this is pure bit manipulation and needs no radio:

- PN9 against the 30 bits printed in 16.2.3.
- The decoder against a reference encoder written *separately* from it,
  rather than by inverting the decoder's own tables.
- A sweep that flips each bit of a frame in turn and requires every one
  to be corrected — this catches a traceback that walks one stage too
  far, which otherwise only shows up as rare, length-dependent failures.
- One real captured frame, asserting both the expected PHR and a valid
  FCS. This is worth more than all the synthetic vectors together: a
  wrong deinterleaver, trellis, whitening phase or bit order does not
  produce a frame whose CRC-32 agrees.

The standard prints no full worked FEC test vector, so there is nothing
to check against but self-consistency and real traffic.


Timing, for a sniffer that wants whole exchanges
------------------------------------------------

Measured on a live FAN network at PhyModeID 0x13, from timestamps taken
at sync detect: **an acknowledgement's SFD lands 2.7 to 3.9 ms after the
end of the frame it answers.** A coded 198-octet frame occupies 32 ms of
air, so the gap is small relative to the frame.

A receiver that is busy for more than about two of those milliseconds
after a frame — decoding it, for instance — will miss the
acknowledgement, and the loss is systematic rather than random: it
affects whichever frame sizes push it over the edge, so it presents as
"some packets are missing" rather than as a decoder fault. Decoding
should not block acquisition of the next frame.

Whether an acknowledgement is expected at all is readable from the MAC
frame control field: bit 5 is the Ack Request bit. It is worth checking
before concluding a frame has gone missing — much of the background
traffic on a FAN network is broadcast and is never acknowledged.


Pitfall checklist
-----------------

Each of these produced a decoder that looked plausible and recovered
nothing, or nearly nothing:

- [ ] Whitening applied to the decoded PSDU instead of to the PSDU's code
      symbols — recovers nothing.
- [ ] Whitening applied over the encoded PHY header as well — five symbol
      errors per frame, all in the first block.
- [ ] PN9 emitting a register bit rather than the feedback term.
- [ ] The encoder's complemented outputs omitted — every recovered bit
      inverted.
- [ ] The PHY header read least-significant-bit first like the rest of
      the frame — `0x1071` instead of `0x088E`.
- [ ] Framing driven by the PHR's Frame Length without doubling it —
      stops halfway through every frame.
- [ ] Traceback walking one stage too far — subtle, length-dependent, and
      caught only by the single-bit-error sweep.
- [ ] Traceback from state 0 rather than from the best surviving state —
      a path metric of 4 on every clean frame from a transmitter that
      pads with ones, which ruins the metric as an oracle.
- [ ] Trusting a 16-bit FCS alone to say a frame was real.
