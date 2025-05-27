from pymongo import MongoClient

try:
    # 连接到MongoDB
    client = MongoClient("mongodb://yintian:ytmongo@me.yintian.vip:7137/")

    # 选择或创建数据库
    db = client["yt_test"]

    # 选择或创建集合
    collection = db["test1"]

    # 插入示例数据
    sample_data = {"name": "1", "age": 1000, "city": "h"}
    result = collection.insert_one(sample_data)
    print(f"Inserted document ID: {result.inserted_id}")

    # 查询数据
    for doc in collection.find():
        print(doc)

    # 关闭连接
    client.close()

except ConnectionError as e:
    print(f"Connection failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")