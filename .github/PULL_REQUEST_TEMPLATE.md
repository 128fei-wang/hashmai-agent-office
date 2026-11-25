## 改了什么

<!-- 一两句话，说清改动和动机 -->

## 为什么

<!-- 关联 issue：Closes #123 / Refs #456 -->

## 怎么验证的

<!-- 贴实际输出，不要写「已测试」 -->

```
$ node tools/test_sim.js
PASS — 9/9

$ python3 tools/check_seat_ids.py --require-unified
SUMMARY seats=23 zones=8 fail=0
```

## 检查清单

- [ ] 改的是 `demo/office-demo.template.html` 或源码，而不是直接手改产物
- [ ] 已重新构建：`python3 tools/build_demo.py`（+ 需要时 `build_single_file.py`）
- [ ] `node tools/test_sim.js` 9/9
- [ ] `python3 tools/check_seat_ids.py --require-unified` rc=0
- [ ] 产物 sha 变化已写在上面的「验证」里（如果变了）
- [ ] 涉及渲染/布局：附改动前后截图
- [ ] 更新了相关文档（README / CHANGELOG / 架构文档）
- [ ] 没有引入网络请求、没有提交凭据
