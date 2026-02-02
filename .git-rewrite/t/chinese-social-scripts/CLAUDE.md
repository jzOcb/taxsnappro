# Chinese Social Media Scripts - RedNote Focus

## Project Purpose
Templates and prompts for creating engaging 小红书 (RedNote) content in Chinese, with personalized style matching.

## Key Files
- `prompts/rednote.md` - Prompt templates for generating posts
- `templates/rednote-post.md` - Post structure template
- `templates/rednote-video-script.md` - Video script template
- `resources/rednote-specs.md` - Platform specs and guidelines
- `resources/writing-style-guide.md` - Personal writing style reference
- `.claude/skills/rednote.md` - RedNote skill definition

## Notion Integration
Past video scripts are stored in Notion under "Videos Schedule" database.
- **Database ID**: `60ca6609-300e-4d66-8548-b7ad9c9df98d`
- Search: `mcp__notion__notion-search` to find scripts
- Fetch: `mcp__notion__notion-fetch` to get full content
- Create: `mcp__notion__notion-create-pages` to save new scripts
- Update: `mcp__notion__notion-update-page` to modify existing scripts

## Skill Commands

### `/rednote` - 创建新脚本
1. Ask for 产品/主题, 视频时长, 内容类型
2. Search Notion for similar past scripts as reference
3. Apply personal writing style from `resources/writing-style-guide.md`
4. Generate script matching established voice and structure
5. **Auto-save to Notion** in "Videos Schedule" database (status: 准备中)

### `/rednote optimize` - 优化已有脚本
1. 从Notion选择脚本 或 直接粘贴内容
2. **WebSearch** 搜索当前小红书流行趋势和叙事风格
3. **WebSearch** 核查产品成分、功效、使用方法
4. 生成优化版本 + 修改报告
5. 选择保存方式：覆盖原脚本 或 创建新版本

## Writing Style (详见 writing-style-guide.md)
- 博主人设: 北美全职码农小经理 + 副业博主
- 口语化表达: 宝子们、直接拉满、闭眼冲、yyds
- 产品描述: 质地→成分→体验→肤质建议
- 真实分享: 优缺点都要提，增加可信度

## Quick Reference
- **标题**: 20字以内，吸引人
- **正文**: 1000字以内，有价值
- **图片**: 3:4竖图，高清美观
- **视频**: 9:16竖屏，最长15分钟
- **标签**: 5-10个相关标签

## Workflow
**Using /rednote skill (推荐):**
1. Run `/rednote`
2. Provide 产品/主题, 视频时长, 内容类型
3. Script auto-generates matching your style
4. Auto-saves to Notion "Videos Schedule" database

**Manual workflow:**
1. Check `resources/rednote-specs.md` for limits
2. Use prompts from `prompts/rednote.md`
3. Follow structure in `templates/rednote-post.md` or `rednote-video-script.md`
4. Save drafts in `scripts/`