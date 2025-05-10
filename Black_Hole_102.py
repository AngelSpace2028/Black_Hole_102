import heapq
import os
import re
import hashlib
import paq
import zlib
from tqdm import tqdm

def build_huffman_tree(frequencies):
    heap = [[weight, [symbol, ""]] for symbol, weight in frequencies.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        lo = heapq.heappop(heap)
        hi = heapq.heappop(heap)
        for pair in lo[1:]:
            pair[1] = "0" + pair[1]
        for pair in hi[1:]:
            pair[1] = "1" + pair[1]
        heapq.heappush(heap, [lo[0] + hi[0]] + lo[1:] + hi[1:])
    return sorted(heapq.heappop(heap)[1:], key=lambda p: p[1])

def create_huffman_codes(tree):
    return {symbol: code for symbol, code in tree}

def load_dictionary_from_file(filename, max_lines=2**24):
    dictionary = {}
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(tqdm(f, total=max_lines, desc="Loading dictionary")):
                if idx >= max_lines:
                    break
                parts = line.strip().split()
                if len(parts) > 0:
                    dictionary[parts[0]] = idx
        return dictionary
    except Exception as e:
        print(f"Dictionary load error: {e}")
        return None

def int_to_3bytes(value):
    return bytes([(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])

def bytes3_to_int(b):
    return (b[0] << 16) | (b[1] << 8) | b[2]

def sha256_hash(data):
    return hashlib.sha256(data).hexdigest()

def compress_text_with_dictionary(text, dictionary):
    result = bytearray()
    tokens = re.findall(r'\S+|\s+', text)
    for token in tqdm(tokens, desc="Encoding words and spaces"):
        if token.isspace():
            result.append(2)
            encoded = token.encode('utf-8')
            result.append(len(encoded))
            result += encoded
        else:
            code = dictionary.get(token)
            if code is not None:
                result.append(1)
                result += int_to_3bytes(code)
            else:
                result.append(0)
                raw = token.encode('utf-8', errors='ignore')
                result.append(len(raw))
                result += raw
    return bytes(result)

def decompress_text_with_dictionary(data, dictionary):
    reverse_dict = {v: k for k, v in dictionary.items()}
    i = 0
    result = []
    while i < len(data):
        flag = data[i]
        i += 1
        if flag == 1:
            if i + 3 > len(data):
                break
            code = bytes3_to_int(data[i:i+3])
            word = reverse_dict.get(code, "")
            result.append(word)
            i += 3
        elif flag == 0:
            if i >= len(data):
                break
            length = data[i]
            i += 1
            word = data[i:i+length].decode('utf-8', errors='ignore')
            result.append(word)
            i += length
        elif flag == 2:
            if i >= len(data):
                break
            length = data[i]
            i += 1
            space = data[i:i+length].decode('utf-8', errors='ignore')
            result.append(space)
            i += length
    return ''.join(result)

def transform_with_pattern(data):
    return bytearray([b ^ 0xFF for b in data])

def compress_bytes_paq_xor(data):
    transformed_data = transform_with_pattern(data)
    return paq.compress(bytes(transformed_data))

def decompress_bytes_paq_xor(data):
    try:
        decompressed_data = paq.decompress(data)
        return transform_with_pattern(bytearray(decompressed_data))
    except Exception as e:
        print(f"Decompression error: {e}")
        return None

def compress_text(input_filename, output_filename, dictionary_filename):
    try:
        dictionary = load_dictionary_from_file(dictionary_filename)
        if dictionary is None:
            print("Failed to load dictionary.")
            return

        text = ""
        with open(input_filename, 'r', encoding='utf-8', errors='ignore') as infile:
            for line in tqdm(infile, desc="Reading text file"):
                text += line

        original_hash = sha256_hash(text.encode('utf-8'))
        encoded = compress_text_with_dictionary(text, dictionary)
        compressed = compress_bytes_paq_xor(encoded)

        with open(output_filename, 'wb') as outfile:
            outfile.write(compressed)

        print(f"Text compressed successfully to {output_filename}")
        print(f"Original SHA-256: {original_hash}")
    except Exception as e:
        print(f"Error: {e}")

def compress_binary(input_filename, output_filename):
    try:
        data = bytearray()
        with open(input_filename, 'rb') as infile:
            while chunk := infile.read(8192):
                data.extend(chunk)
        compressed = compress_bytes_paq_xor(data)
        with open(output_filename, 'wb') as outfile:
            outfile.write(compressed)
        print(f"Binary compressed to {output_filename}")
    except Exception as e:
        print(f"Binary compression error: {e}")

def decompress_binary(input_filename, output_filename):
    try:
        with open(input_filename, 'rb') as infile:
            data = infile.read()

        decompressed = decompress_bytes_paq_xor(data)
        if decompressed is not None:
            choice = input("Use dictionary for decoding? (yes/no): ").lower()
            if choice == 'yes':
                dict_filename = input("Enter dictionary filename: ")
                dictionary = load_dictionary_from_file(dict_filename)
                if dictionary is None:
                    print("Failed to load dictionary.")
                    return
                text = decompress_text_with_dictionary(decompressed, dictionary)
                with open(output_filename, 'w', encoding='utf-8') as outfile:
                    outfile.write(text)
                print(f"Text decompressed to {output_filename}")
                print(f"Decompressed SHA-256: {sha256_hash(text.encode('utf-8'))}")
            else:
                with open(output_filename, 'wb') as outfile:
                    outfile.write(decompressed)
                print(f"Binary decompressed to {output_filename}")
    except Exception as e:
        print(f"Decompression error: {e}")

if __name__ == "__main__":
    print("Choose mode: [1] Compress text, [2] Compress binary, [3] Decompress binary")
    choice = input("Enter choice: ")
    if choice == "1":
        input_filename = input("Enter input text filename: ")
        output_filename = input("Enter output filename: ")
        dictionary_filename = input("Enter dictionary filename: ")
        compress_text(input_filename, output_filename, dictionary_filename)
    elif choice == "2":
        input_filename = input("Enter input binary filename: ")
        output_filename = input("Enter output filename: ")
        compress_binary(input_filename, output_filename)
    elif choice == "3":
        input_filename = input("Enter compressed filename: ")
        output_filename = input("Enter output filename: ")
        decompress_binary(input_filename, output_filename)
    else:
        print("Invalid choice.")
