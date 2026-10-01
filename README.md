# Fruit Recommendation System

**ผู้จัดทำ:** ชิษณุพงศ์ เกตุพูนทอง รหัสนักศึกษา 664245004

โปรเจกต์รายวิชา Graph Database พัฒนาด้วย **Streamlit + Neo4j Aura + Cypher**
และออกแบบให้ deploy ผ่าน **GitHub → Streamlit Community Cloud** ได้โดยตรง

ระบบนี้ต่อยอดจาก notebook `homework/03_neo4j/664245004_fruit_2.ipynb` โดยใช้โครงสร้างกราฟและข้อมูลชุดเดียวกัน
และเพิ่มหน้าจอสำหรับเพิ่ม / แก้ไข / ลบข้อมูลผู้ใช้ ผลไม้ และความสัมพันธ์

## 1. แนวคิดของระบบ

ระบบใช้ Property Graph ดังนี้

```text
(User {name})-[:LIKES]->(Fruit {name, image})
(User)-[:SIMILAR_TO]-(User)
```

- `name` เป็น key ของทั้ง `User` และ `Fruit` (มี unique constraint) จึงไม่มีรหัสแยกต่างหาก
- `SIMILAR_TO` เชื่อมผู้ใช้ที่ชอบผลไม้ชนิดเดียวกันอย่างน้อย 1 ชนิด ระบบสร้างให้จาก `LIKES` ตามวิธีใน notebook และแก้ไขด้วยมือได้ที่เมนูความสัมพันธ์
- `image` คือรูปผลไม้ที่อัปโหลด (ไม่บังคับ) เก็บเป็น byte array ใน node โดยระบบย่อรูปเป็น JPEG ไม่เกิน 480 px ก่อนบันทึก ผลไม้ที่ไม่มีรูปจะแสดงรูปที่ระบบวาดให้

ระบบแนะนำผลไม้ที่ **ผู้ใช้ที่คล้ายกันชอบ แต่เจ้าตัวยังไม่ได้ชอบ**

```text
score = จำนวนผู้ใช้ที่คล้ายกัน (SIMILAR_TO) ที่ชอบผลไม้นั้น
```

คำแนะนำอธิบายได้ (Explainable Recommendation) เพราะระบบแสดงชื่อผู้ใช้ที่คล้ายกันซึ่งชอบผลไม้นั้นประกอบด้วย

> `SIMILAR_TO` ถูกเก็บเพียงหนึ่ง relationship ต่อคู่ และ query แบบไม่สนทิศทาง `-[:SIMILAR_TO]-`
> จึงเป็นความสัมพันธ์สมมาตร: ถ้า A คล้าย B แล้ว B ก็คล้าย A ด้วย

## 2. โครงสร้างไฟล์

```text
664245004pj/
├── app.py                  # Streamlit UI
├── neo4j_service.py        # Cypher + Neo4j Driver
├── requirements.txt
├── .gitignore
├── .streamlit/
│   ├── config.toml         # ธีมของแอป
│   ├── secrets.toml.example
│   └── secrets.toml        # ใส่ password เอง ไม่ถูก commit
├── homework/               # งานที่ 1-3 (แสดงเป็นการ์ดในหน้าหลัก)
│   ├── 01_club/
│   ├── 02_graph/
│   └── 03_neo4j/
├── images/                 # รูปผลไม้ประจำชื่อ (ไม่บังคับ) เช่น images/mango.jpg
├── cypher/
│   ├── schema.cypher
│   └── recommendation.cypher
└── docs/
    └── PROJECT_GUIDE_TH.md
```

## 3. สร้าง Neo4j Aura

1. สร้าง AuraDB instance
2. เก็บค่า Connection URI, username และ password
3. URI ของ Aura โดยทั่วไปอยู่ในรูป `neo4j+s://...databases.neo4j.io`
4. อย่านำ password ไปใส่ในไฟล์ที่ commit ขึ้น GitHub

## 4. รันในเครื่อง

ต้องใช้ **Python 3.10 ขึ้นไป** (ข้อกำหนดของ `neo4j` 6.x และ `streamlit` รุ่นใน `requirements.txt`)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

คัดลอกไฟล์ตัวอย่าง secrets (ถ้ายังไม่มี `.streamlit/secrets.toml`)

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

จากนั้นใส่ password จริงในไฟล์ `.streamlit/secrets.toml` แล้วรัน

```bash
streamlit run app.py
```

## 5. ครั้งแรกที่เปิดระบบ

ถ้ารัน notebook งานที่ 3 กับ Aura instance เดียวกันไว้แล้ว แอปจะเห็นข้อมูลชุดนั้นทันที ไม่ต้องทำอะไรเพิ่ม
ถ้าฐานข้อมูลยังว่าง:

1. เข้าเมนู **⚙️ ตั้งค่าข้อมูล**
2. กด **สร้าง Constraint + ข้อมูลตัวอย่าง** (ผู้ใช้ 10 คน ผลไม้ 5 ชนิด `LIKES` 21 เส้น ตาม notebook)
3. ระบบใช้ `MERGE` จึงกดซ้ำได้โดยไม่สร้าง node ซ้ำ และไม่ลบข้อมูลที่เพิ่มเอง แต่จะคำนวณ `SIMILAR_TO` ใหม่ทั้งระบบ
4. ปุ่ม **ล้างข้อมูลและสร้างข้อมูลตัวอย่างใหม่** จะลบ `User` / `Fruit` ทั้งหมดก่อน (เหมือนขั้นตอนที่ 2 ใน notebook)

## 6. หน้าหลัก (Hub) และเมนูของระบบ

เมื่อเปิดแอปจะเจอหน้าหลักที่รวมงานเป็นการ์ด 4 ใบ หน้านี้ไม่ต้องต่อฐานข้อมูล

- การ์ด 01–03 คือการบ้านในโฟลเดอร์ `homework/` กด "ดูการบ้าน" เพื่อเปิดหน้าของงานนั้น ซึ่งมีชื่อ คำอธิบาย และกรอบแสดงเนื้อหา: notebook `.ipynb` แสดงโค้ดพร้อมผลลัพธ์ที่บันทึกไว้ ส่วน `.pdf` แสดงทีละหน้า
- แต่ละงานมีปุ่มเปิดใน Colab (สำหรับ notebook) ดาวน์โหลดไฟล์ และดูไฟล์บน GitHub
- การ์ด 04 คือระบบแนะนำผลไม้ กด "เข้าสู่ระบบแนะนำ" เพื่อเข้าใช้งาน และกด "← กลับหน้าหลัก" ที่แถบเมนูเพื่อกลับมา
- ชื่อ คำอธิบาย และหัวข้อของแต่ละงานแก้ได้ที่ตัวแปร `HOMEWORK` ใน `app.py`

เมนูภายในระบบแนะนำผลไม้

| เมนู | ทำอะไรได้ |
| --- | --- |
| 📊 ภาพรวม | จำนวน node / relationship, ความนิยมของผลไม้, โปรไฟล์ผู้ใช้ |
| ✨ แนะนำผลไม้ | ผลไม้ที่แนะนำพร้อม score และเหตุผล |
| 👤 ผู้ใช้ | เพิ่ม / เปลี่ยนชื่อ / ลบผู้ใช้ |
| 🍎 ผลไม้ | แกลเลอรีรูปผลไม้, เพิ่ม (พร้อมอัปโหลดรูป) / แก้ไขชื่อและรูป / ลบผลไม้ |
| 🔗 ความสัมพันธ์ | เพิ่ม / ลบ `LIKES` และ `SIMILAR_TO` ของผู้ใช้แต่ละคน และคำนวณ `SIMILAR_TO` ใหม่ทั้งระบบจากผลไม้ที่ชอบร่วมกัน |
| 🕸️ กราฟความสัมพันธ์ | กราฟรอบตัวผู้ใช้ที่เลือก เลือกระยะ 1–3 ทอดและชนิดความสัมพันธ์ได้ |
| ⚙️ ตั้งค่าข้อมูล | ดูการเชื่อมต่อ สร้าง constraint และข้อมูลตัวอย่าง หรือล้างข้อมูลแล้วเริ่มใหม่ |

การลบผู้ใช้หรือผลไม้ใช้ `DETACH DELETE` จึงลบ relationship ที่เกี่ยวข้องไปด้วย
การเปลี่ยนชื่อใช้ `SET` บน node เดิม ความสัมพันธ์ที่มีอยู่จึงไม่หาย

## 7. Deploy GitHub → Streamlit Community Cloud

1. สร้าง GitHub repository ใหม่
2. push ไฟล์ทั้งหมดขึ้น GitHub **ยกเว้น `.streamlit/secrets.toml`**
3. เข้า Streamlit Community Cloud แล้วเลือก Create app
4. เลือก repository, branch และ entrypoint = `app.py`
5. ใน Advanced settings → Secrets ใส่

```toml
[neo4j]
uri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"
username = "YOUR_USERNAME"
password = "YOUR_PASSWORD"
database = "YOUR_DATABASE"
```

6. Deploy

## 8. ประเด็น Graph Database ที่นักศึกษาจะได้ฝึก

- Node, Label, Property
- Relationship และ Direction
- Constraint และ Unique Key
- `MATCH`, `MERGE`, `CREATE`, `SET`, `DELETE`, `DETACH DELETE`, `OPTIONAL MATCH`, `WITH`, `UNWIND`
- Graph traversal ผ่านผู้ใช้ที่คล้ายกัน → ผลไม้
- Aggregation เช่น `count`, `collect`
- Recommendation จาก topology ของกราฟ
- Parameterized Cypher
- Python Driver และ connection pooling
- Streamlit UI
- Secrets และ cloud deployment

## 9. สิ่งที่ปรับปรุงจาก notebook ต้นแบบ

- ข้อมูลตัวอย่างใช้ `MERGE` ทั้งหมด และมีปุ่มเพิ่มข้อมูลแบบไม่ล้างของเดิม
- มอง `SIMILAR_TO` เป็นความสัมพันธ์เชิงสมมาตรตอน query ด้วย `-[:SIMILAR_TO]-` (notebook ข้อ 11 query ตามทิศทาง `->` จึงได้ผลครบเฉพาะผู้ใช้ที่ชื่อมาก่อนตามตัวอักษร)
- เพิ่มหน้าจอ CRUD สำหรับ User, Fruit, `LIKES` และ `SIMILAR_TO`
- คำแนะนำแสดงชื่อผู้ใช้ที่คล้ายกันซึ่งเป็นที่มาของ score
- ใช้ parameterized Cypher แทนการต่อ string จาก input
- แยก database layer (`neo4j_service.py`) ออกจาก UI (`app.py`)
- ใช้ Streamlit Secrets แทนการพิมพ์ password ทุกครั้งหรือ hardcode Aura credential

## 10. แนวทางต่อยอด

สามารถเพิ่ม Login, rating บน `LIKES`, property ของผลไม้ (ฤดูกาล, ราคา, รสชาติ), น้ำหนักของ `SIMILAR_TO` จากสัดส่วนผลไม้ที่ชอบร่วมกัน (Jaccard), Graph Data Science similarity, PageRank, community detection และ evaluation metrics เช่น Precision@K/Recall@K ได้
