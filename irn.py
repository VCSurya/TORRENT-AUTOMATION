import re

# Your regex pattern
pattern = r'\b(?=[0-9a-fA-F]*[a-fA-F])(?=[0-9a-fA-F]*[0-9])[0-9a-fA-F]{10,64}\b'


from itertools import combinations

def get_64_string(lst):
    """
    Takes a list of strings and returns the first string of exactly 64 characters.
    - If any item itself is 64 chars → return it directly.
    - Otherwise, try all possible combinations of items in sequence order.
    - If no such string exists → return empty string.
    """
    # 1️⃣ Direct check: any single item of length 64
    for item in lst:
        if len(item) == 64:
            return item

    n = len(lst)
    # 2️⃣ Try all possible combinations
    for r in range(2, n+1):  # size of combination
        for indices in combinations(range(n), r):
            merged = "".join(lst[i] for i in indices)
            if len(merged) == 64:
                return merged

    # 3️⃣ No solution
    return ""


# Example usage
if __name__ == "__main__":
    
    text = ""

    with open(r"C:\Users\111439\OneDrive - Torrent Gas Ltd\Desktop\TORRENT\all_pdfs_extracted_text\FO2527107304.txt",'r',encoding='utf-8') as f:
        text = str(f.read())

    # Find all matches
    matches = re.findall(pattern, text)
    res = get_64_string(matches)
    print("Result:", res)
    print("Length:", len(res))
