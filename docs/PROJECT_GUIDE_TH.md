# คู่มือสร้างระบบแนะนำผลไม้ด้วย Neo4j Aura และ Streamlit

คู่มือนี้พาสร้างระบบแนะนำผลไม้จากความชอบของผู้ใช้ โดยเก็บข้อมูลเป็นกราฟใน Neo4j Aura เขียนคำแนะนำด้วย Cypher และแสดงผลผ่าน Streamlit

> โครงสร้างกราฟและข้อมูลตัวอย่างในคู่มือนี้ตรงกับ notebook `homework/03_neo4j/664245004_fruit_2.ipynb`: ใช้ label `User` และ `Fruit` โดยมี `name` เป็น key

## 1. สิ่งที่จะได้เรียนรู้

- ออกแบบ Property Graph ด้วย Node, Label, Property และ Relationship
- สร้างข้อกำหนด unique และข้อมูลตัวอย่างด้วย Cypher
- เดินกราฟเพื่อค้นหาผลไม้ที่ผู้ใช้ซึ่งมีความชอบคล้ายกันเลือก
- สร้างคำแนะนำที่อธิบายเหตุผลได้
- เชื่อม Python กับ Neo4j Aura ด้วย Neo4j Python Driver
- สร้างหน้าแอปด้วย Streamlit และจัดการ credential ด้วย Secrets
- เผยแพร่แอปผ่าน GitHub และ Streamlit Community Cloud

## 2. ภาพรวมระบบ

```mermaid
flowchart LR
    U[ผู้ใช้] --> APP[Streamlit: app.py]
    APP --> SVC[บริการฐานข้อมูล: neo4j_service.py]
    SVC --> DB[(Neo4j AuraDB)]
    DB --> SVC
    SVC --> APP
    GH[GitHub] --> CLOUD[Streamlit Community Cloud]
    SECRET[Streamlit Secrets] --> CLOUD
```

- `app.py` แสดงหน้าแรก เมนู และหน้าจัดการข้อมูล
- `neo4j_service.py` เชื่อมต่อฐานข้อมูลและเรียก Cypher
- Neo4j AuraDB จัดเก็บผู้ใช้ ผลไม้ และความสัมพันธ์
- Streamlit Secrets เก็บ URI, username, password และชื่อฐานข้อมูล

## 3. เตรียมเครื่องมือ

ต้องมี Python 3.10 ขึ้นไป, บัญชี Neo4j Aura และ Git หากต้องการ deploy

สร้าง AuraDB instance แล้วจด Connection URI, username, password และ database name ไว้ URI มักมีรูปแบบ `neo4j+s://...databases.neo4j.io` ห้ามใส่ password ลงใน source code หรือ commit ขึ้น GitHub

สร้าง virtual environment และติดตั้ง dependencies จากโฟลเดอร์หลักของโปรเจกต์:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. ออกแบบกราฟ

ในเชิงแนวคิด ระบบประกอบด้วยผู้ใช้ ผลไม้ และความสัมพันธ์ดังนี้:

```mermaid
graph LR
    U1[ผู้ใช้] -- SIMILAR_TO --- U2[ผู้ใช้ที่คล้ายกัน]
    U1 -- LIKES --> F[ผลไม้]
    U2 -- LIKES --> F
```

| องค์ประกอบ | ชื่อในโค้ด/ฐานข้อมูล | Property สำคัญ | ความหมาย |
| --- | --- | --- | --- |
| ผู้ใช้ | `User` | `name` | ผู้ใช้ระบบ |
| ผลไม้ | `Fruit` | `name`, `image` | ผลไม้ที่ระบบจัดเก็บและแนะนำ |
| ความชอบ | `LIKES` | - | ผู้ใช้ชอบผลไม้นั้น |
| ความคล้ายกัน | `SIMILAR_TO` | - | ผู้ใช้สองคนชอบผลไม้ชนิดเดียวกันอย่างน้อย 1 ชนิด |

แม้ `SIMILAR_TO` ถูกเก็บเป็น Relationship ที่มีทิศทางใน Neo4j แต่ query ใช้ `-[:SIMILAR_TO]-` แบบไม่ระบุทิศทาง จึงถือว่าความคล้ายกันสมมาตร

## 5. สร้าง schema และข้อมูลตัวอย่าง

เปิด Neo4j Browser หรือใช้เมนูตั้งค่าข้อมูลในแอปเพื่อสร้าง unique constraint:

```cypher
CREATE CONSTRAINT user_name_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.name IS UNIQUE;

CREATE CONSTRAINT fruit_name_unique IF NOT EXISTS
FOR (f:Fruit) REQUIRE f.name IS UNIQUE;
```

Constraint ป้องกันไม่ให้มี node ผู้ใช้หรือผลไม้ที่ชื่อซ้ำ ส่วนการ seed ใช้ `MERGE` เพื่อให้รันซ้ำได้โดยไม่สร้าง node ซ้ำ:

```cypher
UNWIND $names AS name
MERGE (u:User {name: name});
```

`SIMILAR_TO` สร้างจาก `LIKES` โดยเชื่อมผู้ใช้ทุกคู่ที่ชอบผลไม้ชนิดเดียวกัน เงื่อนไข `u1.name < u2.name` ทำให้ได้หนึ่งเส้นต่อคู่:

```cypher
MATCH (u1:User)-[:LIKES]->(:Fruit)<-[:LIKES]-(u2:User)
WHERE u1.name < u2.name
MERGE (u1)-[:SIMILAR_TO]->(u2);
```

ฟังก์ชัน `seed_demo_data()` ใน `neo4j_service.py` สร้าง constraint ผู้ใช้ 10 คน ผลไม้ 5 ชนิด `LIKES` 21 เส้น แล้วเรียก `rebuild_similar()` เพื่อสร้าง `SIMILAR_TO` (ได้ 32 คู่จากข้อมูลตัวอย่าง)

## 6. หลักการแนะนำผลไม้

อัลกอริทึมเป็น collaborative filtering แบบง่าย:

1. เลือกผู้ใช้เป้าหมาย
2. หาเพื่อนบ้านที่เชื่อมด้วย `SIMILAR_TO`
3. หา `LIKES` ของเพื่อนบ้านเหล่านั้น
4. ตัดผลไม้ที่ผู้ใช้เป้าหมายชอบแล้วออก
5. นับจำนวนเพื่อนบ้านที่ชอบผลไม้แต่ละรายการ แล้วเรียงคะแนนจากมากไปน้อย

```text
คะแนนผลไม้ = จำนวนผู้ใช้ที่คล้ายกันและชอบผลไม้นั้น
```

ตัวอย่าง Cypher ที่สอดคล้องกับ `cypher/recommendation.cypher`:

```cypher
MATCH (me:User {name: $name})
      -[:SIMILAR_TO]-(similar:User)
      -[:LIKES]->(fruit:Fruit)
WHERE NOT EXISTS { MATCH (me)-[:LIKES]->(fruit) }
WITH DISTINCT fruit, similar
RETURN fruit.name AS fruit,
       count(similar) AS score,
       collect(similar.name) AS similar_names
ORDER BY score DESC, fruit
LIMIT $limit;
```

ตัวอย่างจากข้อมูลตัวอย่าง: Ananda ชอบ Mango และ Apple ระบบจึงแนะนำ Banana (score 3), Durian (score 3) และ Grape (score 1) ตรงกับผลใน notebook

`similar_names` ทำให้คำแนะนำอธิบายได้: หน้าจอสามารถบอกได้ว่าผลไม้รายการนั้นถูกแนะนำเพราะผู้ใช้ที่มีความชอบคล้ายกันคนใดเลือกไว้ สูตรคะแนนนี้เหมาะสำหรับเรียนรู้ graph traversal ไม่ใช่การประเมินคุณภาพคำแนะนำระดับงานวิจัย

## 7. เขียน Python เชื่อมต่อ Neo4j

ชั้นบริการใน `neo4j_service.py` สร้าง Neo4j Driver และ cache ด้วย `@st.cache_resource` จากนั้นส่ง Cypher แบบ parameterized ผ่าน `execute_query()`:

```python
cypher = "MATCH (u:User {name: $name}) RETURN u"
parameters = {"name": name}
```

หลีกเลี่ยงการนำ input มาต่อเป็น query string เพราะ parameter แยกข้อมูลออกจากคำสั่ง ทำให้ปลอดภัยและอ่านง่ายกว่า ฟังก์ชัน `recommend_fruits()` ใน service เป็นจุดเรียก query คำแนะนำ

## 8. ตั้งค่า Secrets และรันแอป

คัดลอกไฟล์ตัวอย่าง หากยังไม่มีไฟล์ local:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

ใส่ค่าจริงใน `.streamlit/secrets.toml`:

```toml
[neo4j]
uri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"
username = "YOUR_USERNAME"
password = "YOUR_PASSWORD"
database = "YOUR_DATABASE"
```

ไฟล์ `secrets.toml` ต้องไม่ถูก commit จากนั้นเริ่มแอป:

```bash
streamlit run app.py
```

เมื่อเปิดแอปครั้งแรก เข้าเมนู **ตั้งค่าข้อมูล** แล้วกด **สร้าง Constraint + ข้อมูลตัวอย่าง** เพื่อเตรียมฐานข้อมูล (ข้ามได้ถ้ารัน notebook งานที่ 3 กับ instance เดียวกันไว้แล้ว)

## 9. ทดลองใช้งานหน้าต่าง ๆ

| เมนู | การทำงาน |
| --- | --- |
| ภาพรวม | ดูจำนวน node/relationship ความนิยมของผลไม้ และโปรไฟล์ผู้ใช้ |
| แนะนำผลไม้ | เลือกผู้ใช้ กำหนดจำนวนผลลัพธ์ และดูคะแนนพร้อมเหตุผล |
| ผู้ใช้ | เพิ่ม เปลี่ยนชื่อ และลบผู้ใช้ |
| ผลไม้ | ดูรายการ เพิ่ม แก้ไข ลบ และจัดการรูปภาพ |
| ความสัมพันธ์ | เพิ่ม/ลบ `LIKES` และ `SIMILAR_TO` ของผู้ใช้ และคำนวณ `SIMILAR_TO` ใหม่จากผลไม้ที่ชอบร่วมกัน |
| กราฟความสัมพันธ์ | สำรวจ node และ relationship รอบผู้ใช้ที่เลือก ในระยะ 1–3 ทอด |
| ตั้งค่าข้อมูล | ดูการเชื่อมต่อ สร้าง constraint และข้อมูลตัวอย่าง หรือล้างข้อมูลแล้วเริ่มใหม่ |

การลบ node ใช้ `DETACH DELETE` จึงลบ relationship ที่ติดอยู่กับ node นั้นด้วย รูปที่อัปโหลดจะถูกย่อก่อนจัดเก็บ ผลไม้ที่ยังไม่ได้อัปโหลดรูปจะใช้รูปใน `images/` ตามชื่อ ถ้าไม่มีจะแสดงรูปที่ระบบวาดให้

## 10. CRUD และการจัดการความสัมพันธ์

ตัวอย่างคำสั่งเปลี่ยนชื่อผู้ใช้ เนื่องจาก `name` เป็น key จึงต้องตรวจว่าชื่อใหม่ยังไม่มีใครใช้ ความสัมพันธ์เดิมยังอยู่เพราะแก้ที่ node เดิม:

```cypher
MATCH (u:User {name: $name})
WHERE NOT EXISTS { MATCH (x:User {name: $new_name}) WHERE x <> u }
SET u.name = $new_name;
```

เพิ่มความชอบโดยไม่สร้าง relationship ซ้ำ:

```cypher
MATCH (u:User {name: $user})
MATCH (f:Fruit {name: $fruit})
MERGE (u)-[:LIKES]->(f);
```

ลบผู้ใช้พร้อมความสัมพันธ์ทั้งหมด:

```cypher
MATCH (u:User {name: $name})
DETACH DELETE u;
```

`neo4j_service.py` รวมการทำงาน CRUD และจัดการความสัมพันธ์ไว้เป็นฟังก์ชัน เช่น `create_user()`, `rename_user()`, `delete_user()`, `create_fruit()`, `set_likes()`, `set_similar()` และ `rebuild_similar()` เพื่อให้ UI ไม่ต้องประกอบ query เอง

การแก้ `LIKES` ในแอปไม่เปลี่ยน `SIMILAR_TO` ให้อัตโนมัติ ถ้าต้องการให้ `SIMILAR_TO` ตรงกับความชอบล่าสุด ให้กดคำนวณใหม่ที่แท็บ `SIMILAR_TO` ซึ่งจะแทนที่ความสัมพันธ์ที่แก้ด้วยมือทั้งหมด

## 11. Deploy บน Streamlit Community Cloud

1. Push โปรเจกต์ขึ้น GitHub โดยไม่รวม `.streamlit/secrets.toml`
2. สร้างแอปใน Streamlit Community Cloud แล้วเลือก repository และ branch
3. กำหนด entrypoint เป็น `app.py`
4. เพิ่มค่า `[neo4j]` ในส่วน Advanced settings → Secrets โดยใช้ credential ของ Aura
5. Deploy และตรวจสอบ log หากเชื่อมต่อฐานข้อมูลไม่ได้

Streamlit Cloud ติดตั้ง package จาก `requirements.txt` และใช้ Secrets ที่ตั้งไว้ในหน้า deploy แทนไฟล์ local

## 12. ลำดับฝึกปฏิบัติและแนวทางต่อยอด

1. วาด graph model และอธิบายทิศทางของ `LIKES` กับ `SIMILAR_TO`
2. สร้าง constraint และ seed node/relationship ด้วย `UNWIND` และ `MERGE`
3. ทดลอง `MATCH`, `WHERE`, `WITH`, `RETURN` และ `ORDER BY`
4. ไล่เส้นทางจากผู้ใช้ไปยังผู้ใช้ที่คล้ายกัน แล้วไปยังผลไม้ที่ชอบ
5. เพิ่ม aggregation ด้วย `count()` และหลักฐานด้วย `collect()`
6. เปรียบเทียบผลเมื่อเปลี่ยนวิธีคำนวณความคล้ายหรือคะแนน
7. ต่อด้วย rating, ราคา/คุณสมบัติผลไม้, Jaccard similarity, Graph Data Science หรือ Precision@K และ Recall@K
