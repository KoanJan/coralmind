EVALUATION_STANDARD = """
## Task Execution Result Evaluation Standard

### 1. Evaluation Objective

Score the final output of AI task execution to assess how well the output meets the original task requirements.

### 2. Evaluation Dimensions

1. **Completeness** (Weight: 30%)
   - Whether all required content of the task is completed
   - Whether key information or steps are missing
   - Whether the output content is comprehensive

2. **Accuracy** (Weight: 30%)
   - Whether the output content is accurate and error-free
   - Whether there are factual errors
   - Whether the information is precise and reliable

3. **Relevance** (Weight: 25%)
   - Whether the output closely aligns with task requirements
   - Whether irrelevant content is included
   - Whether key points are highlighted

4. **Quality** (Weight: 15%)
   - Professionalism of the output
   - Clarity of expression
   - Coherence of logic

### 3. Scoring Criteria

| Score Range | Grade | Description |
|-------------|-------|-------------|
| 9-10 | Excellent | Fully meets task requirements, exceptional performance across all dimensions, no obvious defects |
| 7-8 | Good | Basically meets task requirements, good performance across all dimensions, minor room for improvement |
| 5-6 | Average | Partially meets task requirements, obvious deficiencies in some dimensions |
| 3-4 | Poor | Barely completes the task, serious issues in multiple dimensions |
| 0-2 | Failed | Does not complete task requirements, extremely low output quality or off-topic |

### 4. Scoring Principles

1. **Objective and Fair**: Score based on task requirements and actual output, avoid subjective bias

2. **Comprehensive Consideration**: Comprehensively evaluate performance across all dimensions, not relying on a single aspect

3. **Strict Standards**: Give lower scores for missing key information or serious errors

4. **Recognize Excellence**: Give high scores for performance that exceeds expectations

### 5. Scoring Process

1. Carefully read the original task requirements
2. Thoroughly review the actual output content
3. Evaluate each dimension one by one
4. Give a final score (integer from 0-10) based on all dimensions

### 6. Examples

**Task Requirements**:
```text
Summarize the core points of this article and list the key data supporting each point
```

**Output Example A** (9 points):
- Completely summarized all core points
- Provided accurate data support for each point
- Clear structure, professional expression

**Output Example B** (6 points):
- Summarized main points but missed secondary points
- Some data missing or inaccurate
- Average structure

**Output Example C** (3 points):
- Only mentioned partial points
- Many data errors
- Confusing expression
"""
