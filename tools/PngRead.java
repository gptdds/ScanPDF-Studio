import java.awt.image.BufferedImage;
import java.io.File;
import java.io.InputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import javax.imageio.ImageIO;

public final class PngRead {
    public static void main(String[] args) throws Exception {
        BufferedImage image;
        if (args.length == 2) {
            try (ZipFile zip = new ZipFile(args[0]);
                 InputStream stream = zip.getInputStream(new ZipEntry(args[1]))) {
                image = ImageIO.read(stream);
            }
        } else {
            image = ImageIO.read(new File(args[0]));
        }
        if (image == null) {
            throw new IllegalStateException("ImageIO returned null");
        }
        System.out.println(image.getWidth() + "x" + image.getHeight());
    }
}
