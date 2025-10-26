import struct


class MPLS:

    """
    Object containing information on Blu-ray MPLS files
    """
    def __init__(self, filename):
        """
        Parse a Blu-ray MPLS file
        :param str filename: path to the mpls file to be parsed
        :rtype: :class:`MPLS`.
        :raises ValueError: if parsing fails
        """
        # Create a read handle for the MPLS file
        f = open(filename, mode="rb")

        # ====== #
        # Header #
        # ====== #
        self.Header = {}
        self.Header["TypeIndicator"] = f.read(4)
        self.Header["VersionNumber"] = f.read(4)
        self.Header["PlayListStartAddress"], = struct.unpack(u">I", f.read(4))
        self.Header["PlayListMarkStartAddress"], = struct.unpack(u">I", f.read(4))
        self.Header["ExtensionDataStartAddress"], = struct.unpack(u">I", f.read(4))
        f.read(20)  # 160 reserved bits

        # Parse MVC Base View Flag from misc flags at offset 0x38
        f.seek(0x38)
        misc_flags, = struct.unpack(u">B", f.read(1))
        self.MVCBaseViewR = (misc_flags & 0x10) != 0  # 4th bit

        # =============== #
        # AppInfoPlayList #
        # =============== #
        f.seek(0x40)  # Return to AppInfoPlayList position
        self.AppInfoPlayList = {}
        self.AppInfoPlayList["Length"], = struct.unpack(u">I", f.read(4))
        f.read(1)  # 8 reserved bits
        self.AppInfoPlayList["PlaybackType"], = struct.unpack(u">B", f.read(1))
        if self.AppInfoPlayList["PlaybackType"] == int(0x02) or self.AppInfoPlayList["PlaybackType"] == int(0x03):
            self.AppInfoPlayList["PlaybackCount"], = struct.unpack(u">H", f.read(2))
        else:
            f.read(2)  # 16 reserved bits
        self.AppInfoPlayList["UOMaskTable"], = struct.unpack(u">Q", f.read(8))
        self.AppInfoPlayList["MiscFlags"], = struct.unpack(u">H", f.read(2))

        # ======== #
        # PlayList #
        # ======== #
        f.seek(self.Header["PlayListStartAddress"])
        self.PlayList = {}
        self.PlayList["Length"], = struct.unpack(u">I", f.read(4))
        StartPosition = f.tell()
        f.read(2)  # 16 reserved bits
        self.PlayList["NumberOfPlayItems"], = struct.unpack(u">H", f.read(2))
        self.PlayList["NumberOfSubPaths"], = struct.unpack(u">H", f.read(2))
        # Loop over PlayItems ...
        self.PlayList["PlayItems"] = []
        for _ in range(self.PlayList["NumberOfPlayItems"]):
            self.PlayList["PlayItems"].append(self.get_play_item(f))
        self.PlayList["SubPaths"] = []
        for _ in range(self.PlayList["NumberOfSubPaths"]):
            self.PlayList["SubPaths"].append(self.get_sub_path(f))
        # go to the end of the playlist data
        f.seek(StartPosition + self.PlayList["Length"])

        # Calculate playlist-level AngleCount (maximum angle count from all play items)
        self.PlayList["AngleCount"] = 0
        for play_item in self.PlayList["PlayItems"]:
            if play_item["IsMultiAngle"] and play_item["AngleCount"] > self.PlayList["AngleCount"]:
                self.PlayList["AngleCount"] = play_item["AngleCount"]

        # ============ #
        # PlayListMark #
        # ============ #
        f.seek(self.Header["PlayListMarkStartAddress"])
        self.PlayListMarks = {}
        self.PlayListMarks["Length"], = struct.unpack(u">I", f.read(4))
        StartPosition = f.tell()
        self.PlayListMarks["NumberOfPlayListMarks"], = struct.unpack(u">H", f.read(2))
        self.PlayListMarks["PlayListMarks"] = []
        for _ in range(self.PlayListMarks["NumberOfPlayListMarks"]):
            PlayListMark = {}
            f.read(1)  # 8 reserved bits
            PlayListMark["MarkType"], = struct.unpack(u">B", f.read(1))
            PlayListMark["RefToPlayItemID"], = struct.unpack(u">H", f.read(2))
            PlayListMark["MarkTimeStamp"], = struct.unpack(u">I", f.read(4))
            PlayListMark["EntryESPID"], = struct.unpack(u">H", f.read(2))
            PlayListMark["Duration"], = struct.unpack(u">I", f.read(4))
            self.PlayListMarks["PlayListMarks"].append(PlayListMark)
        # go to the end of the playlist mark data
        f.seek(StartPosition + self.PlayListMarks["Length"])

        # ============= #
        # ExtensionData #
        # ============= #
        self.ExtensionData = {}
        if self.Header["ExtensionDataStartAddress"]:
            f.seek(self.Header["ExtensionDataStartAddress"])
            self.ExtensionData["Length"], = struct.unpack(u">I", f.read(4))
            StartPosition = f.tell()
            if self.ExtensionData["Length"]:
                self.ExtensionData["DataBlockStartAddress"] = struct.unpack(u">I", f.read(4))
                f.read(3)  # 24 reserved bits
                self.ExtensionData["NumberOfExtDataEntries"] = struct.unpack(u">I", f.read(1))
                self.ExtensionData["ExtDataEntries"] = []
                for _ in range(self.ExtensionData["NumberOfExtDataEntries"]):
                    ExtDataEntry = {}
                    ExtDataEntry["ExtDataType"] = struct.unpack(u">I", f.read(2))
                    ExtDataEntry["ExtDataVersion"] = struct.unpack(u">I", f.read(2))
                    ExtDataEntry["ExtDataStartAddress"] = struct.unpack(u">I", f.read(4))
                    ExtDataEntry["ExtDataLength"] = struct.unpack(u">I", f.read(4))
                    self.ExtensionData["ExtDataEntries"].append(ExtDataEntry)
            # go to the end of the extension data
            f.seek(StartPosition + self.ExtensionData["Length"])

    def get_sub_path(self, f):
        SubPath = {}
        SubPath["Length"], = struct.unpack(u">I", f.read(4))
        StartPosition = f.tell()
        f.read(1)  # 8 reserved bits
        SubPath["SubPathType"], = struct.unpack(u">B", f.read(1))
        f.read(1)  # 8 reserved bits
        b, = struct.unpack(u">B", f.read(1))  # first 7 bits are reserved
        SubPath["IsRepeatSubPath"] = b & 0b00000001
        f.read(1)  # 8 reserved bits
        SubPath["NumberOfSubPlayItems"], = struct.unpack(u">B", f.read(1))
        SubPath["SubPlayItems"] = []
        for _ in range(SubPath["NumberOfSubPlayItems"]):
            SubPath["SubPlayItems"].append(self.get_sub_play_item(f))
        # go to the end of the play item data
        f.seek(StartPosition + SubPath["Length"])
        return SubPath

    def get_sub_play_item(self, f):
        SubPlayItem = {}
        SubPlayItem["Length"], = struct.unpack(u">H", f.read(2))
        StartPosition = f.tell()
        SubPlayItem["ClipInformationFileName"] = f.read(5).decode("utf-8")
        SubPlayItem["ClipCodecIdentifier"] = f.read(4).decode("utf-8")
        f.read(3)   # 24 reserved bits
        b, = struct.unpack(u">B", f.read(1))  # first 3 bits are reserved
        SubPlayItem["ConnectionCondition"] = b & 0b00011110
        SubPlayItem["IsMultiClipEntries"] = b & 0b00000001
        SubPlayItem["RefToSTCID"], = struct.unpack(u">B", f.read(1))
        SubPlayItem["INTime"], = struct.unpack(u">I", f.read(4))
        SubPlayItem["OUTTime"], = struct.unpack(u">I", f.read(4))
        SubPlayItem["SyncPlayItemID"], = struct.unpack(u">H", f.read(2))
        SubPlayItem["SyncStartPTS"], = struct.unpack(u">I", f.read(4))
        if SubPlayItem["IsMultiClipEntries"]:
            SubPlayItem["NumberOfMultiClipEntries"], = struct.unpack(u">H", f.read(1))
            f.read(1)  # 8 reserved bits
            SubPlayItem["MultiClipEntries"] = []
            for _ in range(SubPlayItem["NumberOfMultiClipEntries"]):
                MultiClipEntry = {}
                MultiClipEntry["ClipInformationFileName"] = f.read(5).decode("utf-8")
                MultiClipEntry["ClipCodecIdentifier"] = f.read(5).decode("utf-8")
                MultiClipEntry["RefToSTCID"], = struct.unpack(u">B", f.read(1))
                SubPlayItem["MultiClipEntries"].append(MultiClipEntry)
        # go to the end of the play item data
        f.seek(StartPosition + SubPlayItem["Length"])
        return SubPlayItem

    def get_play_item(self, f):
        PlayItem = {}
        PlayItem["Length"], = struct.unpack(u">H", f.read(2))
        StartPosition = f.tell()
        PlayItem["ClipInformationFileName"] = f.read(5).decode("utf-8")
        PlayItem["ClipCodecIdentifier"] = f.read(4).decode("utf-8")

        # Parse flags byte
        flags_byte, = struct.unpack(u">B", f.read(1))
        PlayItem["IsMultiAngle"] = (flags_byte >> 4) & 0x01
        PlayItem["ConnectionCondition"] = flags_byte & 0x0F

        # Parse multi-angle flags byte if multi-angle is enabled
        if PlayItem["IsMultiAngle"]:
            multi_angle_flags, = struct.unpack(u">B", f.read(1))
            PlayItem["IsDifferentAudios"] = (multi_angle_flags >> 2) & 0x3F  # 6 bits
            PlayItem["IsSeamlessAngleChange"] = multi_angle_flags & 0x01     # 1 bit
        else:
            # Don't read reserved byte to match old version's file position exactly
            pass

        PlayItem["RefToSTCID"], = struct.unpack(u">B", f.read(1))
        PlayItem["INTime"], = struct.unpack(u">I", f.read(4))
        PlayItem["OUTTime"], = struct.unpack(u">I", f.read(4))
        PlayItem["UOMaskTable"], = struct.unpack(u">Q", f.read(8))

        # Parse PlayItem flags
        playitem_flags, = struct.unpack(u">B", f.read(1))
        PlayItem["PlayItemRandomAccessFlag"] = (playitem_flags >> 7) & 0x01
        f.read(1)  # 7 reserved bits

        PlayItem["StillMode"], = struct.unpack(u">B", f.read(1))
        if PlayItem["StillMode"] == int(0x01):
            PlayItem["StillTime"], = struct.unpack(u">H", f.read(2))
        else:
            f.read(2)  # 16 reserved bits

        # Handle multi-angle clips - only if multi-angle is enabled
        PlayItem["AngleClips"] = []
        PlayItem["AngleCount"] = 0
        if PlayItem["IsMultiAngle"]:
            # Read number of angles
            number_of_angles, = struct.unpack(u">B", f.read(1))
            f.read(1)  # 1 reserved byte

            # Parse angle clips (angles - 1 additional angles)
            for angle_index in range(number_of_angles - 1):
                angle_clip = {}
                angle_clip["ClipInformationFileName"] = f.read(5).decode("utf-8")
                angle_clip["ClipCodecIdentifier"] = f.read(4).decode("utf-8")
                f.read(1)  # 1 reserved byte
                PlayItem["AngleClips"].append(angle_clip)

            PlayItem["AngleCount"] = number_of_angles - 1

        PlayItem["STNTable"] = self.get_stn_table(f)
        # go to the end of the play item data
        f.seek(StartPosition + PlayItem["Length"])
        return PlayItem

    def get_stn_table(self, f):
        STNTable = {}
        STNTable["Length"], = struct.unpack(u">H", f.read(2))
        StartPosition = f.tell()
        f.read(2)  # 16 reserved bits
        # read entry counts - separate primary and secondary streams
        for item in [
            "PrimaryVideoStreamEntries", "PrimaryAudioStreamEntries",
            "PrimaryPGStreamEntries", "PrimaryIGStreamEntries",
            "SecondaryAudioStreamEntries", "SecondaryVideoStreamEntries",
            "SecondaryPGStreamEntries", "DVStreamEntries"
        ]:
            STNTable[f"NumberOf{item}"], = struct.unpack(u">B", f.read(1))
        f.read(4)  # 32 reserved bits

        # Parse primary streams
        for item in [
            "PrimaryVideoStreamEntries", "PrimaryAudioStreamEntries",
            "PrimaryPGStreamEntries", "PrimaryIGStreamEntries"
        ]:
            STNTable[item] = []
            for _ in range(STNTable[f"NumberOf{item}"]):
                STNTable[item].append({
                    "StreamEntry": self.get_stream_entry(f),
                    "StreamAttributes": self.get_stream_attributes(f)
                })

        # Parse secondary streams separately
        for item in [
            "SecondaryAudioStreamEntries", "SecondaryVideoStreamEntries",
            "SecondaryPGStreamEntries", "DVStreamEntries"
        ]:
            STNTable[item] = []
            for _ in range(STNTable[f"NumberOf{item}"]):
                STNTable[item].append({
                    "StreamEntry": self.get_stream_entry(f),
                    "StreamAttributes": self.get_stream_attributes(f)
                })

        # go to the end of the table data
        f.seek(StartPosition + STNTable["Length"])
        return STNTable

    def get_stream_entry(self, f):
        StreamEntry = {}
        StreamEntry["Length"], = struct.unpack(u">B", f.read(1))
        StartPosition = f.tell()
        if StreamEntry["Length"]:
            StreamEntry["StreamType"], = struct.unpack(u">B", f.read(1))
            if StreamEntry["StreamType"] == int(0x01):
                StreamEntry["RefToStreamPID"], = struct.unpack(u">H", f.read(2))
                StreamEntry["RefToStreamPID"] = "0x{0:<04x}".format(StreamEntry["RefToStreamPID"])
            elif StreamEntry["StreamType"] == int(0x02):
                StreamEntry["RefToSubPathID"], = struct.unpack(u">B", f.read(1))
                StreamEntry["RefToSubClipID"], = struct.unpack(u">B", f.read(1))
                StreamEntry["RefToStreamPID"], = struct.unpack(u">H", f.read(2))
                StreamEntry["RefToStreamPID"] = "0x{0:<04x}".format(StreamEntry["RefToStreamPID"])
            elif StreamEntry["StreamType"] == int(0x03) or StreamEntry["StreamType"] == int(0x04):
                StreamEntry["RefToSubPathID"], = struct.unpack(u">B", f.read(1))
                StreamEntry["RefToStreamPID"], = struct.unpack(u">H", f.read(2))
                StreamEntry["RefToStreamPID"] = "0x{0:<04x}".format(StreamEntry["RefToStreamPID"])
        # go to the end of the stream entry data
        f.seek(StartPosition + StreamEntry["Length"])
        return StreamEntry

    def get_stream_attributes(self, f):
        StreamAttributes = {}
        StreamAttributes["Length"], = struct.unpack(u">B", f.read(1))
        StartPosition = f.tell()
        if StreamAttributes["Length"]:
            StreamAttributes["StreamCodingType"], = struct.unpack(u">B", f.read(1))

            # Extended video stream support
            if StreamAttributes["StreamCodingType"] in [
                int(0x01), int(0x02), int(0x1B), int(0x20), int(0xEA), int(0x24)
            ]:
                b, = struct.unpack(u">B", f.read(1))
                StreamAttributes["VideoFormat"] = b >> 4
                StreamAttributes["FrameRate"] = b & 0b1111

                # Read aspect ratio for video streams (except MVC)
                if StreamAttributes["StreamCodingType"] != int(0x20):
                    b, = struct.unpack(u">B", f.read(1))
                    StreamAttributes["AspectRatio"] = b >> 4

            # HEVC specific attributes
            if StreamAttributes["StreamCodingType"] in [int(0x24)]:  # HEVC
                b, = struct.unpack(u">B", f.read(1))
                StreamAttributes["DynamicRangeType"] = b >> 4
                StreamAttributes["ColorSpace"] = b & 0b1111
                b, = struct.unpack(u">B", f.read(1))
                StreamAttributes["CRFlag"] = (b & 0b10000000) >> 7
                StreamAttributes["HDRPlusFlag"] = (b & 0b01000000) >> 6

            # Enhanced audio stream attributes with detailed parsing
            if StreamAttributes["StreamCodingType"] in [
                int(0x03), int(0x04), int(0x80), int(0x81), int(0x82), int(0x83),
                int(0x84), int(0x85), int(0x86), int(0xA1), int(0xA2)
            ]:
                b, = struct.unpack(u">B", f.read(1))
                StreamAttributes["AudioFormat"] = b >> 4
                StreamAttributes["SampleRate"] = b & 0b1111
                # Audio attributes
                StreamAttributes["ChannelLayout"] = self.get_channel_layout(b >> 4)
                StreamAttributes["SampleRateHz"] = self.get_sample_rate_hz(b & 0b1111)

                StreamAttributes["LanguageCode"] = f.read(3).decode("utf-8")

            # Graphics streams
            if StreamAttributes["StreamCodingType"] in [int(0x90), int(0x91)]:
                StreamAttributes["LanguageCode"] = f.read(3).decode("utf-8")

            if StreamAttributes["StreamCodingType"] in [int(0x92)]:
                char_code, = struct.unpack(u">B", f.read(1))
                StreamAttributes["CharacterCode"] = char_code
                StreamAttributes["CharacterCodeName"] = self.get_character_code_name(char_code)
                StreamAttributes["LanguageCode"] = f.read(3).decode("utf-8")

        # go to the end of the stream attribute data
        f.seek(StartPosition + StreamAttributes["Length"])
        return StreamAttributes

    def get_channel_layout(self, layout_code):
        """Convert channel layout code to descriptive name"""
        channel_layouts = {
            1: "Mono",
            3: "Stereo",
            6: "Multi-channel",
            12: "Combo"
        }
        return channel_layouts.get(layout_code, "Unknown")

    def get_sample_rate_hz(self, sample_rate_code):
        """Convert sample rate code to Hz value"""
        sample_rates = {
            1: 48000,
            4: 96000,
            5: 192000,
            12: [48000, 192000],  # 48/192 combo
            14: [48000, 96000]    # 48/96 combo
        }
        return sample_rates.get(sample_rate_code, 0)

    def get_character_code_name(self, char_code):
        """Convert character code to descriptive name"""
        character_codes = {
            0x01: "UTF-8",
            0x02: "UTF-16BE",
            0x03: "Shift-JIS",
            0x04: "EUC-KR",
            0x05: "GB18030",
            0x06: "Big5",
            0x07: "ISO-8859-1",
            0x08: "ISO-8859-2",
            0x09: "ISO-8859-3",
            0x0A: "ISO-8859-4",
            0x0B: "ISO-8859-5",
            0x0C: "ISO-8859-6",
            0x0D: "ISO-8859-7",
            0x0E: "ISO-8859-8",
            0x0F: "ISO-8859-9",
            0x10: "ISO-8859-10",
            0x11: "ISO-8859-11",
            0x12: "ISO-8859-13",
            0x13: "ISO-8859-14",
            0x14: "ISO-8859-15"
        }
        return character_codes.get(char_code, "Unknown")

    def get_bits(self, b):
        if not isinstance(b, bytearray) and not isinstance(b, bytes):
            raise ValueError("pympls.MPLS.get_bits: Bad argument value")
        return [i for sl in [
            [((b[0] >> i) & 1) for i in range(8)
        ] for x in b] for i in sl]

    def __repr__(self):
        return "<MPLS " + ", ".join([
            f"Header={self.Header}",
            f"AppInfoPlayList={self.AppInfoPlayList}",
            f"PlayList={self.PlayList}",
            f"PlayListMarks={self.PlayListMarks}",
            f"ExtensionData={self.ExtensionData}",
            f"MVCBaseViewR={self.MVCBaseViewR}"
        ]) + ">"
