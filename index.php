<?php
// --- 动态配置 ---
$imageBaseDir = 'api_ready_images';
$apiBaseUrl = "http" . (isset($_SERVER['HTTPS']) ? "s" : "") . "://" . $_SERVER['HTTP_HOST'] . dirname($_SERVER['REQUEST_URI']);

// 自动获取图片库中的标签名
$tagDirs = array_diff(scandir($imageBaseDir), ['..', '.']);
$tagName = reset($tagDirs) ?: '未知标签';

// --- 新增：计算每种分类的图片数量 ---
$available_orientations = ['horizontal', 'vertical', 'square'];
$image_counts = [];
$total_count = 0;

/**
 * 获取指定分类下的图片数量
 * @param string $baseDir 基础目录
 * @param string $tag 标签名
 * @param string $orientation 分类名
 * @return int 图片数量
 */
function getImageCount($baseDir, $tag, $orientation) {
    $manifest_path = implode(DIRECTORY_SEPARATOR, [$baseDir, $tag, $orientation, 'manifest.json']);
    if (!file_exists($manifest_path)) {
        return 0;
    }
    $image_list = json_decode(file_get_contents($manifest_path), true);
    return is_array($image_list) ? count($image_list) : 0;
}

foreach ($available_orientations as $orient) {
    $count = getImageCount($imageBaseDir, $tagName, $orient);
    $image_counts[$orient] = $count;
    $total_count += $count;
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>~//: 随机图床 API v1.0 ://~</title>
    <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>小石头随机图床API<span id="cursor">_</span></h1>
            <p class="subtitle">>>> 一个为爱发电的随机图片API, 由PHP强力驱动。</p>
            <p>>>> 当前图库: [ <strong><?php echo htmlspecialchars($tagName); ?></strong> ]</p>
        </header>

        <main>
            <fieldset>
                <legend>API 使用说明</legend>
                <p>本API通过直接输出图片的方式工作，可以直接在 `<img>` 标签或CSS的 `url()` 中使用。</p>
                
                <h3>// 基本接口 (完全随机)</h3>
                <p>从所有图片中随机返回一张 (总计: <?php echo $total_count; ?> 张)。</p>
                <code><?php echo $apiBaseUrl; ?>/api.php</code>
                <a href="api.php" class="try-button" target="_blank">[ 执行 ]</a>

                <h3>// 分类接口 (指定方向)</h3>
                <p>通过添加 `orientation` 参数来获取特定方向的图片。</p>
                <ul>
                    <li>
                        <strong>获取横图 (horizontal)</strong>
                        <span class="count">[当前数量: <?php echo $image_counts['horizontal']; ?>]</span>
                        <code><?php echo $apiBaseUrl; ?>/api.php?orientation=horizontal</code>
                        <a href="api.php?orientation=horizontal" class="try-button" target="_blank">[ 执行 ]</a>
                    </li>
                    <li>
                        <strong>获取竖图 (vertical)</strong>
                        <span class="count">[当前数量: <?php echo $image_counts['vertical']; ?>]</span>
                        <code><?php echo $apiBaseUrl; ?>/api.php?orientation=vertical</code>
                        <a href="api.php?orientation=vertical" class="try-button" target="_blank">[ 执行 ]</a>
                    </li>
                    <li>
                        <strong>获取方图 (square)</strong>
                        <span class="count">[当前数量: <?php echo $image_counts['square']; ?>]</span>
                        <code><?php echo $apiBaseUrl; ?>/api.php?orientation=square</code>
                        <a href="api.php?orientation=square" class="try-button" target="_blank">[ 执行 ]</a>
                    </li>
                </ul>
            </fieldset>

            <fieldset>
                <legend>使用示例</legend>
                <p>下面这张图片就是通过调用 `/api.php` 随机获取的：</p>
                <div class="image-preview-container">
                    <div class="image-preview">
                        <img src="api.php?t=<?php echo time(); ?>" alt="随机图片">
                    </div>
                </div>
                <small>（刷新页面可看到不同的图片...）</small>
            </fieldset>
        </main>
        
        <footer>
            <p>STATUS: OK. SYSTEM READY.</p>
            <p>由fulie构建。</p>
        </footer>
    </div>
</body>
</html>